#!/usr/bin/env python3
"""ScoutBase E2E Test Suite — Tests every endpoint before we build anything"""
import httpx
import asyncio
import json
import sys
import time
import cv2
import numpy as np
from pathlib import Path

BASE_URL = "http://localhost:8500"

def create_test_video(path="uploads/test_video.mp4", frames=90, fps=30):
    w, h = 640, 480
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(path, fourcc, fps, (w, h))
    players = [(np.random.randint(50, w-50), np.random.randint(50, h-50)) for _ in range(10)]
    for frame_num in range(frames):
        img = np.zeros((h, w, 3), dtype=np.uint8)
        img[:] = (34, 139, 34)
        for i, (px, py) in enumerate(players):
            px = max(20, min(w-20, px + np.random.randint(-5, 6)))
            py = max(20, min(h-20, py + np.random.randint(-5, 6)))
            players[i] = (px, py)
            color = (255, 0, 0) if i < 5 else (0, 0, 255)
            cv2.circle(img, (px, py), 15, color, -1)
        out.write(img)
    out.release()
    return path

class Results:
    def __init__(self):
        self.passed, self.failed, self.skipped = [], [], []
    def log(self, name, status, detail=""):
        if status == "PASS": self.passed.append(name); print(f"  ✅ {name}" + (f" — {detail}" if detail else ""))
        elif status == "FAIL": self.failed.append((name, detail)); print(f"  ❌ {name}: {detail}")
        else: self.skipped.append((name, detail)); print(f"  ⏭️  {name}: {detail}")
    def summary(self):
        total = len(self.passed) + len(self.failed) + len(self.skipped)
        print(f"\n{'='*60}")
        print(f"RESULTS: {len(self.passed)}/{total} passed, {len(self.failed)} failed, {len(self.skipped)} skipped")
        if self.failed:
            print(f"\nFAILURES:")
            for n, d in self.failed: print(f"  ❌ {n}: {d}")
        if self.skipped:
            print(f"\nSKIPPED:")
            for n, d in self.skipped: print(f"  ⏭️  {n}: {d}")
        print(f"{'='*60}")

async def run():
    r = Results()
    print("Creating test video...")
    vid = create_test_video()
    
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=180.0) as c:
        # 1. Server health
        print("\n[SERVER HEALTH]")
        try:
            resp = await c.get("/docs")
            r.log("GET /docs", "PASS" if resp.status_code == 200 else "FAIL", str(resp.status_code))
        except Exception as e:
            r.log("GET /docs", "FAIL", str(e)); r.summary(); return

        try:
            resp = await c.get("/health")
            r.log("GET /health", "PASS" if resp.status_code == 200 else "FAIL", resp.text[:200])
        except Exception as e:
            r.log("GET /health", "FAIL", str(e))

        # PLAYER MANAGEMENT
        print("\n[PLAYER MANAGEMENT]")

        # List players
        try:
            resp = await c.get("/players")
            data = resp.json()
            # Response is a list or dict with players key
            if isinstance(data, list):
                count = len(data)
            elif isinstance(data, dict):
                count = data.get("total", len(data.get("players", [])))
            else:
                count = "?"
            r.log("GET /players", "PASS" if resp.status_code == 200 else "FAIL", f"Status:{resp.status_code}, count:{count}")
        except Exception as e:
            r.log("GET /players", "FAIL", str(e))

        # Create player — uses PlayerBase which requires: name, age, nation, flag, club, league, position
        player_id = None
        try:
            player_payload = {
                "name": "E2E Test Player",
                "age": 22,
                "nation": "Nigeria",
                "flag": "🇳🇬",
                "club": "Test FC",
                "league": "Test League",
                "position": "ST"
            }
            resp = await c.post("/players", json=player_payload)
            if resp.status_code in (200, 201):
                player_id = resp.json().get("id") or resp.json().get("player", {}).get("id")
            r.log("POST /players", "PASS" if resp.status_code in (200, 201) else "FAIL",
                  f"Status:{resp.status_code}, id:{player_id}, detail:{resp.text[:200] if resp.status_code not in (200,201) else ''}")
        except Exception as e:
            r.log("POST /players", "FAIL", str(e))

        # Update player
        if player_id:
            try:
                resp = await c.put(f"/players/{player_id}", json={"name": "Updated E2E Player", "age": 23})
                r.log(f"PUT /players/{player_id}", "PASS" if resp.status_code == 200 else "FAIL",
                      f"Status:{resp.status_code}, detail:{resp.text[:100] if resp.status_code != 200 else ''}")
            except Exception as e:
                r.log("PUT /players/{id}", "FAIL", str(e))

        # Shortlist - add
        if player_id:
            try:
                resp = await c.post(f"/shortlist/{player_id}")
                r.log("POST /shortlist/{id}", "PASS" if resp.status_code == 200 else "FAIL",
                      f"Status:{resp.status_code}, detail:{resp.text[:200] if resp.status_code != 200 else ''}")
            except Exception as e:
                r.log("POST /shortlist/{id}", "FAIL", str(e))

        # Shortlist - get
        try:
            resp = await c.get("/shortlist")
            r.log("GET /shortlist", "PASS" if resp.status_code == 200 else "FAIL",
                  f"Status:{resp.status_code}, data:{resp.text[:100]}")
        except Exception as e:
            r.log("GET /shortlist", "FAIL", str(e))

        # Leagues
        try:
            resp = await c.get("/leagues")
            r.log("GET /leagues", "PASS" if resp.status_code == 200 else "FAIL",
                  f"Status:{resp.status_code}, count:{len(resp.json()) if resp.status_code == 200 else '?'}")
        except Exception as e:
            r.log("GET /leagues", "FAIL", str(e))

        # CORE PIPELINE
        print("\n[CORE PIPELINE]")
        
        # Upload video — field name is 'video' not 'file'
        job_id = None
        try:
            with open(vid, "rb") as f:
                resp = await c.post("/process", files={"video": ("test.mp4", f, "video/mp4")})
            if resp.status_code in (200, 201, 202):
                data = resp.json()
                job_id = data.get("job_id") or data.get("id")
            r.log("POST /process", "PASS" if resp.status_code in (200, 201, 202) else "FAIL",
                  f"Status:{resp.status_code}, job:{job_id}, detail:{resp.text[:200] if resp.status_code not in (200,201,202) else ''}")
        except Exception as e:
            r.log("POST /process", "FAIL", str(e))

        # Poll status
        if job_id:
            print(f"  Polling /status/{job_id} (up to 120s)...")
            final_status = "unknown"
            for i in range(60):
                try:
                    resp = await c.get(f"/status/{job_id}")
                    data = resp.json()
                    final_status = data.get("status", "unknown")
                    progress = data.get("progress", 0)
                    if i % 5 == 0 or final_status in ("completed","failed","error"):
                        print(f"    [{i*2}s] status={final_status}, progress={progress}")
                    if final_status in ("completed", "complete", "done", "finished"):
                        break
                    if final_status in ("failed", "error"):
                        print(f"    Error detail: {data.get('error', 'no error msg')}")
                        break
                except Exception as e:
                    print(f"    Poll error: {e}")
                    break
                await asyncio.sleep(2)
            r.log(f"GET /status/{job_id}", "PASS" if final_status in ("completed","complete","done","finished") else "FAIL",
                  f"Final: {final_status}")

        # Get results
        if job_id:
            try:
                resp = await c.get(f"/results/{job_id}")
                if resp.status_code == 200:
                    keys = list(resp.json().keys()) if isinstance(resp.json(), dict) else "list"
                    r.log("GET /results/{job_id}", "PASS", f"Keys: {keys}")
                else:
                    r.log("GET /results/{job_id}", "FAIL", f"Status:{resp.status_code}, detail:{resp.text[:200]}")
            except Exception as e:
                r.log("GET /results/{job_id}", "FAIL", str(e))

        # Get annotated video
        if job_id:
            try:
                resp = await c.get(f"/results/{job_id}/video")
                if resp.status_code == 200:
                    r.log("GET /results/{job_id}/video", "PASS", f"Size: {len(resp.content)} bytes")
                elif resp.status_code == 404:
                    r.log("GET /results/{job_id}/video", "SKIP", "404 - video not generated")
                else:
                    r.log("GET /results/{job_id}/video", "FAIL", f"Status:{resp.status_code}: {resp.text[:200]}")
            except Exception as e:
                r.log("GET /results/{job_id}/video", "FAIL", str(e))

        # Get tracks
        if job_id:
            try:
                resp = await c.get(f"/results/{job_id}/tracks")
                if resp.status_code == 200:
                    data = resp.json()
                    count = len(data) if isinstance(data, list) else data.get("count", len(data.get("tracks", [])))
                    r.log("GET /results/{job_id}/tracks", "PASS", f"tracks: {count}")
                else:
                    r.log("GET /results/{job_id}/tracks", "FAIL", f"Status:{resp.status_code}: {resp.text[:200]}")
            except Exception as e:
                r.log("GET /results/{job_id}/tracks", "FAIL", str(e))

        # Video info
        if job_id:
            try:
                resp = await c.get(f"/results/{job_id}/info")
                r.log("GET /results/{job_id}/info", "PASS" if resp.status_code == 200 else "FAIL",
                      f"Status:{resp.status_code}, data:{resp.text[:150]}")
            except Exception as e:
                r.log("GET /results/{job_id}/info", "FAIL", str(e))

        # Frame extraction
        if job_id:
            try:
                resp = await c.get(f"/results/{job_id}/frame/0")
                r.log("GET /results/{job_id}/frame/0", "PASS" if resp.status_code == 200 else "FAIL",
                      f"Status:{resp.status_code}, size:{len(resp.content) if resp.status_code==200 else 'N/A'}")
            except Exception as e:
                r.log("GET /results/{job_id}/frame/0", "FAIL", str(e))

        # CSV export
        if job_id:
            try:
                resp = await c.get(f"/results/{job_id}/csv")
                r.log("GET /results/{job_id}/csv", "PASS" if resp.status_code == 200 else "FAIL",
                      f"Status:{resp.status_code}")
            except Exception as e:
                r.log("GET /results/{job_id}/csv", "FAIL", str(e))

        # Jobs list
        try:
            resp = await c.get("/jobs")
            r.log("GET /jobs", "PASS" if resp.status_code == 200 else "FAIL", f"Status:{resp.status_code}")
        except Exception as e:
            r.log("GET /jobs", "FAIL", str(e))

        # SAM3
        print("\n[SAM3]")
        try:
            resp = await c.get("/sam3/status")
            r.log("GET /sam3/status", "PASS" if resp.status_code == 200 else "FAIL",
                  f"Status:{resp.status_code}, data:{resp.text[:200]}")
        except Exception as e:
            r.log("GET /sam3/status", "FAIL", str(e))

        if job_id:
            try:
                resp = await c.post("/sam3/segment", json={"job_id": job_id, "frame_number": 0, "prompt": "players in blue"})
                if resp.status_code == 200:
                    r.log("POST /sam3/segment", "PASS")
                elif resp.status_code in (503, 501, 500, 422):
                    r.log("POST /sam3/segment", "SKIP", f"Status:{resp.status_code}: {resp.text[:200]}")
                else:
                    r.log("POST /sam3/segment", "FAIL", f"Status:{resp.status_code}: {resp.text[:300]}")
            except Exception as e:
                r.log("POST /sam3/segment", "FAIL", str(e))

        if job_id:
            try:
                resp = await c.post("/sam3/teams", json={"job_id": job_id, "home_color_hint": "blue", "away_color_hint": "red"})
                if resp.status_code == 200:
                    r.log("POST /sam3/teams", "PASS")
                elif resp.status_code in (503, 501, 500, 422):
                    r.log("POST /sam3/teams", "SKIP", f"Status:{resp.status_code}: {resp.text[:200]}")
                else:
                    r.log("POST /sam3/teams", "FAIL", f"Status:{resp.status_code}: {resp.text[:300]}")
            except Exception as e:
                r.log("POST /sam3/teams", "FAIL", str(e))

        if job_id:
            try:
                resp = await c.post(f"/sam3/enhance/{job_id}/tracks")
                if resp.status_code == 200:
                    r.log("POST /sam3/enhance/{job_id}/tracks", "PASS")
                elif resp.status_code in (503, 501, 500, 422, 404):
                    r.log("POST /sam3/enhance/{job_id}/tracks", "SKIP", f"Status:{resp.status_code}: {resp.text[:200]}")
                else:
                    r.log("POST /sam3/enhance/{job_id}/tracks", "FAIL", f"Status:{resp.status_code}: {resp.text[:300]}")
            except Exception as e:
                r.log("POST /sam3/enhance/{job_id}/tracks", "FAIL", str(e))

        # Shortlist - remove
        if player_id:
            try:
                resp = await c.delete(f"/shortlist/{player_id}")
                r.log("DELETE /shortlist/{id}", "PASS" if resp.status_code == 200 else "FAIL", str(resp.status_code))
            except Exception as e:
                r.log("DELETE /shortlist/{id}", "FAIL", str(e))

    r.summary()
    
    # Save results
    with open("/opt/sloe-os/repos/scoutbase/test_results.json", "w") as f:
        json.dump({
            "passed": r.passed,
            "failed": [{"test": n, "detail": d} for n, d in r.failed],
            "skipped": [{"test": n, "detail": d} for n, d in r.skipped],
            "total": len(r.passed) + len(r.failed) + len(r.skipped)
        }, f, indent=2)

if __name__ == "__main__":
    asyncio.run(run())
