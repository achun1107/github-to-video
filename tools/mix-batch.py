# -*- coding: utf-8 -*-
"""批量混音 v2：不用 loudnorm（它会重新平衡各层），改成固定增益 + 单级峰值限制。

  python tools/mix-batch.py <工程目录>
"""
import subprocess
import sys
from pathlib import Path


def dur(p):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                          '-of', 'default=nw=1:nk=1', str(p)], capture_output=True, text=True)
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0


def main():
    proj = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
    raw = proj / 'renders/raw.mp4'
    if not raw.exists():
        sys.exit('no raw.mp4')
    bed = proj / 'audio/bgm/edm-cut.wav'
    if not bed.exists():
        sys.exit('no bgm')
    vo1 = proj / 'audio/vo1.mp3'
    score = proj / 'audio/score.wav'
    out = proj / 'renders/final.mp4'
    end = dur(raw)

    # 预裁 BGM 到片子长度
    bed18 = proj / 'audio/bgm/bed18.wav'
    if not bed18.exists():
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(bed), '-t', f'{end:.3f}',
                        '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s16le', str(bed18)], check=True)

    inputs = ['-i', str(raw), '-i', str(bed18)]
    idx = 2
    sc_i, vo_i = None, None
    if score.exists():
        inputs += ['-i', str(score)]
        sc_i = idx; idx += 1
    if vo1.exists():
        inputs += ['-i', str(vo1)]
        vo_i = idx

    f = []
    # 人声：带通 110–4500、+10dB、0.6s 起、侧链源
    if vo_i is not None:
        f.append(f'[{vo_i}:a]aresample=48000,pan=stereo|c0=c0|c1=c0,highpass=f=110,lowpass=f=4500,'
                 f'volume=3.3,adelay=600|600[vox0];[vox0]asplit=2[voA][voS]')
    # BGM：单层，低音略抬；人声侧链压到底噪
    duck = ('[mu0][voS]sidechaincompress=threshold=0.010:ratio=12:attack=4:release=320:level_sc=1[mu1];'
            if vo_i is not None else '[mu0]anull[mu1];')
    f.append(f'[1:a]aresample=48000,atrim=0:{end:.3f},asetpts=N/SR/TB,'
             f'volume=0.20,afade=t=in:st=0:d=0.25,afade=t=out:st={end-0.7:.3f}:d=0.7,'
             f'pan=stereo|c0=c0|c1=c0[mu0];{duck}'
             f'[mu1]anull[mus]')

    labels = '[mus]'
    if sc_i is not None:
        f.append(f'[{sc_i}:a]aresample=48000,volume=0.07[snd]')
        labels += '[snd]'
    if vo_i is not None:
        labels += '[voA]'
    n_in = labels.count('[')
    # 混音后只做峰值限制（不动各层比例）
    f.append(f'{labels}amix=inputs={n_in}:normalize=0:dropout_transition=0[a0];'
             f'[a0]alimiter=limit=0.85:attack=5:release=60:level=disabled[an]')

    cmd = ['ffmpeg', '-hide_banner', '-y'] + inputs + [
        '-filter_complex', ';'.join(f),
        '-map', '0:v', '-map', '[an]',
        '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-ar', '48000',
        '-movflags', '+faststart', '-t', f'{end:.3f}', str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(r.stderr[-600:])
    print(f'done {out} {dur(out):.2f}s')


if __name__ == '__main__':
    main()
