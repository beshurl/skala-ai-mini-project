"""Shared deterministic judgments and deployment delta calculations."""

def assess(data, settings):
    if data.get("status") not in ("healthy", "degraded", "down"):
        return "정보 부족"
    if data["cpu_percent"] >= settings.cpu_warning or data["memory_percent"] >= settings.memory_warning or data.get("alerts") or data["status"] != "healthy":
        return "주의"
    return "정상"


def compare(before, after, settings):
    if not before or not after:
        return {"verdict": "정보 부족", "reason": "전후 스냅샷이 모두 필요합니다.", "deltas": {}}
    deltas = {"cpu_pp": round(after["cpu_percent"] - before["cpu_percent"], 2),
              "memory_pp": round(after["memory_percent"] - before["memory_percent"], 2),
              "alerts": len(after.get("alerts", [])) - len(before.get("alerts", []))}
    new_alerts = [a for a in after.get("alerts", []) if a not in before.get("alerts", [])]
    verdict = assess(after, settings)
    if verdict == "정상" and (deltas["cpu_pp"] >= settings.cpu_delta_warning or deltas["memory_pp"] >= settings.memory_delta_warning or new_alerts):
        verdict = "주의"
    return {"verdict": verdict, "deltas": deltas, "new_alerts": new_alerts,
            "reason": "배포 인과관계는 스냅샷 비교만으로 확정할 수 없습니다."}
