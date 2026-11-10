# -*- coding: utf-8 -*-
"""把人声、音效、背景音乐混进画面（支持人声侧链 ducking）。

  python tools/mix.py <工程目录>
  python tools/mix.py <工程目录> --music audio/bgm/edm-cut.wav --music-gain 0.22 --vo-gain 1.35 --duck
  python tools/mix.py <工程目录> --music x.mp3 --lufs -14 --tp -1.0 --no-vo

三层电平：
  人声    --vo-gain    1.35   ← 解说是主体，这次整体抬了 2.6 dB
  音效    --bg         0.10   ← tick / chord 点缀
  配乐    --music-gain 0.20   ← 纯音乐垫底

--duck：用「人声总线」反过来压配乐（threshold -26dB / ratio 6 / attack 8ms / release 220ms）。
  人声一响，配乐自动退 4–6 dB；人声停了再抬回来。这样"人声更大"和"音乐更炸"可以同时成立。
"""
import subprocess
import sys
from pathlib import Path


def dur(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", str(path)],
                         capture_output=True, text=True)
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    proj = Path(a[0]).resolve()

    def opt(name, default):
        return float(a[a.index(name) + 1]) if name in a else default

    def sopt(name, default):
        return a[a.index(name) + 1] if name in a else default

    vo1_at = opt("--vo1", 0.6)
    vo2_at = opt("--vo2", 21.1)
    bg = opt("--bg", 0.06)
    music_gain = opt("--music-gain", 0.20)
    vo_gain = opt("--vo-gain", 1.8)
    duck = "--duck" in a
    use_vo = "--no-vo" not in a
    music_path = sopt("--music", None)

    raw = proj / "renders/raw.mp4"
    if not raw.exists():
        sys.exit(f"没有 {raw}，先跑 render.py")
    score = proj / "audio/score.wav"
    vo1 = proj / "audio/vo1.mp3"
    vo2 = proj / "audio/vo2.mp3"
    out = proj / "renders/final.mp4"
    end = dur(raw)

    inputs = ["-i", str(raw)]
    idx = 1
    music_idx = score_idx = None
    vo_idx = []

    if music_path:
        mp = Path(music_path)
        if not mp.is_absolute():
            mp = (proj / music_path).resolve()
        if not mp.exists():
            sys.exit(f"找不到配乐 {mp}")
        inputs += ["-stream_loop", "-1", "-i", str(mp)]
        music_idx = idx
        idx += 1

    if score.exists():
        inputs += ["-i", str(score)]
        score_idx = idx
        idx += 1

    if use_vo:
        for p in (vo1, vo2):
            if p.exists():
                inputs += ["-i", str(p)]
                vo_idx.append(idx)
                idx += 1
            else:
                vo_idx.append(None)
                print(f"跳过 {p.name}（不存在）")

    filters = []
    vo_label = None

    # ── 人声总线（先算，配乐要用它做侧链）
    if any(vo_idx):
        tags = []
        for k, i in enumerate(vo_idx):
            if i is None:
                continue
            at = vo1_at if k == 0 else vo2_at
            ms = int(round(at * 1000))
            filters.append(
                f"[{i}:a]aresample=48000,pan=stereo|c0=c0|c1=c0,volume={vo_gain},"
                f"adelay={ms}|{ms}[v{k}]")
            tags.append(f"[v{k}]")
        if len(tags) == 1:
            filters.append(f"{tags[0]}anull[vox]")
        else:
            filters.append(f"{''.join(tags)}amix=inputs={len(tags)}:normalize=0:dropout_transition=0[vox]")
        if duck and music_idx is not None:
            filters.append("[vox]asplit=2[voA][voS]")
            vo_label = "voA"
        else:
            filters.append("[vox]anull[voA]")
            vo_label = "voA"

    # ── 配乐（可被人声侧链压低）
    if music_idx is not None:
        filters.append(
            f"[{music_idx}:a]aresample=48000,atrim=0:{end:.3f},asetpts=N/SR/TB,"
            f"volume={music_gain},"
            f"afade=t=in:st=0:d=0.35,afade=t=out:st={end - 1.2:.3f}:d=1.2,"
            f"pan=stereo|c0=c0|c1=c0[mu0]")
        if duck and vo_label:
            filters.append(
                "[mu0][voS]sidechaincompress=threshold=0.020:ratio=7:attack=6:release=260:"
                "makeup=1:level_sc=1[mu]")
        else:
            filters.append("[mu0]anull[mu]")

    mix_in = []
    if music_idx is not None:
        mix_in.append("[mu]")
    if score_idx is not None:
        filters.append(f"[{score_idx}:a]aresample=48000,volume={bg}[bg]")
        mix_in.append("[bg]")
    if vo_label:
        mix_in.append(f"[{vo_label}]")

    if not mix_in:
        sys.exit("没有任何音频输入")

    if len(mix_in) == 1:
        filters.append(f"{mix_in[0]}anull[a]")
    else:
        filters.append(f"{''.join(mix_in)}amix=inputs={len(mix_in)}:normalize=0:dropout_transition=0[a]")

    lufs = opt("--lufs", -14.0)
    tp = opt("--tp", -1.0)
    if "--no-loudnorm" not in a:
        thr = opt("--comp-thresh", -24.0)
        ratio = opt("--comp-ratio", 4.0)
        makeup = opt("--comp-makeup", 3.0)
        filters.append(f"[a]acompressor=threshold={thr}dB:ratio={ratio}:attack=4:release=80:"
                       f"makeup={makeup}[ac]")
        filters.append(f"[ac]loudnorm=I={lufs}:TP={tp}:LRA=11[an]")
        out_label = "[an]"
    else:
        out_label = "[a]"

    cmd = ["ffmpeg", "-hide_banner", "-y"] + inputs + [
        "-filter_complex", ";".join(filters),
        "-map", "0:v", "-map", out_label,
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart", "-t", f"{end:.3f}", str(out),
    ]
    print(" ".join(cmd))
    subprocess.run(cmd, check=True)
    print(f"done {out}  video={end:.2f}s audio={dur(out):.2f}s  duck={'on' if duck else 'off'} vo_gain={vo_gain}")


if __name__ == "__main__":
    main()
