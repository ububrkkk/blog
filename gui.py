from __future__ import annotations

import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Dict, List, Tuple

from .expansion import expand_with_profile, expand_with_suffixes
from .providers import GoogleSuggestProvider, NaverSuggestProvider
from .scoring import (
    KeywordScore,
    score_keywords,
    score_keywords_with_metrics,
    score_keywords_by_platform,
)
from .enrichers import build_enrichers_from_env, enrich_keywords, EnrichedMetrics
from .text_utils import normalize_query, unique_ordered
from .env import load_env


def _collect_suggestions_gui(
    seeds: List[str], provider_names: List[str], depth: int, hl: str
) -> Tuple[List[str], Dict[str, int]]:
    provider_names = [p.strip().lower() for p in provider_names]
    providers = []
    if "naver" in provider_names:
        providers.append(NaverSuggestProvider())
    if "google" in provider_names:
        providers.append(GoogleSuggestProvider())

    all_candidates: List[str] = []
    hit_counts: Dict[str, int] = {}

    def _accumulate(cands: List[str]) -> None:
        for kw in cands:
            all_candidates.append(kw)
            hit_counts[kw] = hit_counts.get(kw, 0) + 1

    # round 1
    for p in providers:
        if isinstance(p, GoogleSuggestProvider):
            _accumulate(p.bulk_suggest(seeds, hl=hl))
        else:
            _accumulate(p.bulk_suggest(seeds))

    if depth >= 2:
        suffix_expanded = expand_with_suffixes(seeds)
        for p in providers:
            if isinstance(p, GoogleSuggestProvider):
                _accumulate(p.bulk_suggest(suffix_expanded, hl=hl))
            else:
                _accumulate(p.bulk_suggest(suffix_expanded))

    return unique_ordered(all_candidates), hit_counts


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        # Load .env for API keys
        load_env()
        self.title("블로그 키워드 분석기 (Naver/Tistory)")
        self.geometry("760x640")
        self._build_widgets()

    def _build_widgets(self) -> None:
        pad = {"padx": 6, "pady": 4}

        frm = tk.Frame(self)
        frm.pack(fill=tk.BOTH, expand=False)

        tk.Label(frm, text="시드 키워드 (줄 단위)").grid(row=0, column=0, sticky="w", **pad)
        self.txt_seeds = tk.Text(frm, height=6)
        self.txt_seeds.grid(row=1, column=0, columnspan=6, sticky="nsew", **pad)

        self.var_nav = tk.BooleanVar(value=True)
        self.var_ggl = tk.BooleanVar(value=True)
        tk.Checkbutton(frm, text="Naver", variable=self.var_nav).grid(row=2, column=0, sticky="w", **pad)
        tk.Checkbutton(frm, text="Google", variable=self.var_ggl).grid(row=2, column=1, sticky="w", **pad)

        tk.Label(frm, text="깊이(Depth)").grid(row=2, column=2, sticky="e", **pad)
        self.var_depth = tk.IntVar(value=2)
        tk.Spinbox(frm, from_=1, to=2, textvariable=self.var_depth, width=5).grid(row=2, column=3, sticky="w", **pad)

        tk.Label(frm, text="프로필").grid(row=2, column=4, sticky="e", **pad)
        self.var_profile = tk.StringVar(value="")
        tk.OptionMenu(frm, self.var_profile, "", "travel", "food").grid(row=2, column=5, sticky="w", **pad)

        self.var_suffix = tk.BooleanVar(value=False)
        tk.Checkbutton(frm, text="롱테일 접미사 포함", variable=self.var_suffix).grid(row=3, column=0, columnspan=2, sticky="w", **pad)

        tk.Label(frm, text="Limit").grid(row=3, column=2, sticky="e", **pad)
        self.var_limit = tk.IntVar(value=300)
        tk.Entry(frm, textvariable=self.var_limit, width=8).grid(row=3, column=3, sticky="w", **pad)

        tk.Label(frm, text="Top 미리보기").grid(row=3, column=4, sticky="e", **pad)
        self.var_top = tk.IntVar(value=50)
        tk.Entry(frm, textvariable=self.var_top, width=8).grid(row=3, column=5, sticky="w", **pad)

        self.var_enrich = tk.BooleanVar(value=False)
        tk.Checkbutton(frm, text="API 보정 사용", variable=self.var_enrich).grid(row=4, column=0, sticky="w", **pad)

        tk.Label(frm, text="Enrich Limit").grid(row=4, column=2, sticky="e", **pad)
        self.var_enrich_limit = tk.IntVar(value=200)
        tk.Entry(frm, textvariable=self.var_enrich_limit, width=8).grid(row=4, column=3, sticky="w", **pad)

        # Platform selection
        tk.Label(frm, text="플랫폼").grid(row=5, column=0, sticky="w", **pad)
        self.var_pf_naver = tk.BooleanVar(value=True)
        self.var_pf_tistory = tk.BooleanVar(value=True)
        tk.Checkbutton(frm, text="네이버", variable=self.var_pf_naver).grid(row=5, column=1, sticky="w", **pad)
        tk.Checkbutton(frm, text="티스토리", variable=self.var_pf_tistory).grid(row=5, column=2, sticky="w", **pad)

        tk.Label(frm, text="출력 CSV").grid(row=6, column=0, sticky="w", **pad)
        self.var_output = tk.StringVar(value="results.csv")
        tk.Entry(frm, textvariable=self.var_output, width=40).grid(row=6, column=1, columnspan=3, sticky="w", **pad)
        tk.Button(frm, text="찾아보기", command=self._browse_output).grid(row=6, column=4, sticky="w", **pad)

        tk.Button(frm, text="실행", command=self.run).grid(row=6, column=5, sticky="e", **pad)

        # Result area
        self.txt_log = tk.Text(self, height=20)
        self.txt_log.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

    def _browse_output(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if path:
            self.var_output.set(path)

    def run(self) -> None:
        thread = threading.Thread(target=self._run_impl, daemon=True)
        thread.start()

    def _append_log(self, msg: str) -> None:
        self.txt_log.insert(tk.END, msg + "\n")
        self.txt_log.see(tk.END)

    def _run_impl(self) -> None:
        try:
            seeds_text = self.txt_seeds.get("1.0", tk.END).strip()
            seeds = [normalize_query(s) for s in seeds_text.splitlines() if normalize_query(s)]
            if not seeds:
                messagebox.showwarning("입력 필요", "시드 키워드를 1개 이상 입력하세요.")
                return

            providers: List[str] = []
            if self.var_nav.get():
                providers.append("naver")
            if self.var_ggl.get():
                providers.append("google")
            if not providers:
                providers = ["google"]

            depth = int(self.var_depth.get())
            profile = self.var_profile.get() or None
            include_suffix = bool(self.var_suffix.get())
            limit = int(self.var_limit.get())
            top = int(self.var_top.get())
            enrich = bool(self.var_enrich.get())
            enrich_limit = int(self.var_enrich_limit.get())
            output = self.var_output.get()
            platforms: List[str] = []
            if self.var_pf_naver.get():
                platforms.append("naver")
            if self.var_pf_tistory.get():
                platforms.append("tistory")
            if not platforms:
                platforms = ["naver", "tistory"]

            self._append_log("[i] 제안 수집 중...")
            candidates, hit_counts = _collect_suggestions_gui(seeds, providers, depth=depth, hl="ko")
            if profile:
                candidates = unique_ordered(candidates + expand_with_profile(seeds, profile))
            elif include_suffix:
                candidates = unique_ordered(candidates + expand_with_suffixes(seeds))
            if limit:
                candidates = candidates[:limit]

            self._append_log(f"[i] 후보 {len(candidates)}개 점수화...")
            metrics_map: Dict[str, EnrichedMetrics] | None = None
            if enrich:
                enr = build_enrichers_from_env()
                if not enr:
                    self._append_log("[!] ENV에 API 키가 설정되지 않아 휴리스틱으로 진행합니다.")
                metrics_map = enrich_keywords(candidates, enr, limit=enrich_limit)

            # Per-platform scoring
            per_platform: Dict[str, List[KeywordScore]] = {}
            for pf in platforms:
                if metrics_map is not None:
                    per_platform[pf] = score_keywords_by_platform(
                        candidates, hit_counts=hit_counts, metrics=metrics_map, platform=pf
                    )
                else:
                    per_platform[pf] = score_keywords(candidates, hit_counts=hit_counts)

            # Preview per platform
            for pf in platforms:
                pf_scores = per_platform[pf]
                self._append_log(f"[i] [{pf.upper()}] 상위 {min(top, len(pf_scores))}개:")
                for row in pf_scores[:top]:
                    self._append_log(
                        f"- {row.keyword} | 기회 {row.opportunity:.2f} / 수요 {row.demand:.2f} / 경쟁 {row.competition:.2f} (hits {row.provider_hits})"
                    )

            # CSV per platform
            if output:
                from .cli import _write_csv  # reuse CSV writer

                prefix = output[:-4] if output.lower().endswith(".csv") else output
                for pf in platforms:
                    path = f"{prefix}.{pf}.csv"
                    _write_csv(path, per_platform[pf], metrics_map)
                    self._append_log(f"[i] [{pf.upper()}] CSV 저장 완료: {path}")

            messagebox.showinfo("완료", "분석이 완료되었습니다.")
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("오류", str(e))


def main() -> int:
    app = App()
    app.mainloop()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
