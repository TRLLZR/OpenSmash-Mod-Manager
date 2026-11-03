"""JSON worker boundary for the native browser; independent of deployment workers."""

import argparse, json, sys
from pathlib import Path
import gamebanana as gb
from downloads import Queue, updates


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument(
        "action",
        choices=(
            "config",
            "browse",
            "detail",
            "image",
            "enqueue",
            "status",
            "control",
            "run",
            "updates",
            "preview",
            "link",
            "remove",
            "clear",
            "save",
            "library-images",
            "set-preview",
        ),
    )
    a = parser.parse_args()
    raw = sys.stdin.read(1048577)
    if len(raw) > 1048576:
        raise ValueError("Netzwerkanfrage zu gross.")
    payload = json.loads(raw or "{}")
    root = a.repo / "opensmash_mods"
    import modmanager as m

    m.load(a.repo)  # manager ownership + recovery before repository access
    client = gb.Client(root / "network-cache")
    if a.action == "library-images":
        import library_media

        return library_media.populate(
            a.repo,
            client,
            payload.get("ids"),
            lambda event: print(json.dumps(event), flush=True),
        )
    if a.action == "set-preview":
        import library_media

        key = payload.get("id")
        if key not in m.load(a.repo)["mods"]:
            raise ValueError("Mod nicht mehr installiert.")
        return dict(
            id=key, path=library_media.set_cover(a.repo, key, payload.get("source", ""))
        )
    if a.action == "config":
        return client.config()
    if a.action == "browse":
        result = client.browse(
            **{
                k: payload[k]
                for k in ("query", "model", "category", "sort", "page", "character")
                if k in payload
            }
        )
        installed = {
            (r.get("origin", {}).get("model"), r.get("origin", {}).get("submission_id"))
            for r in m.listing(a.repo)["mods"]
        }
        for row in result["items"]:
            row["installed"] = (row["model"], row["id"]) in installed
        return result
    if a.action == "detail":
        return client.detail(payload.get("model"), payload.get("id"))
    if a.action == "image":
        return dict(
            path=client.thumbnail(
                payload.get("url", ""), full=bool(payload.get("full"))
            ),
            url=payload.get("url"),
        )
    if a.action == "updates":
        return updates(a.repo, client)
    queue = Queue(a.repo, client)
    if a.action == "link":
        import manager_links

        return manager_links.accept(queue, payload.get("url"))
    if a.action == "enqueue":
        return queue.enqueue(
            payload.get("model"), payload.get("id"), payload.get("file_id")
        )
    if a.action == "status":
        return dict(items=queue.jobs())
    if a.action == "remove":
        return queue.remove(payload.get("ids"))
    if a.action == "clear":
        return queue.clear()
    if a.action == "save":
        return queue.save(payload.get("id"), payload.get("destination"))
    if a.action == "control":
        return queue.control(payload.get("id"), payload.get("action"))
    if a.action == "preview":
        return queue.preview(
            payload.get("ids"), lambda event: print(json.dumps(event), flush=True)
        )
    return queue.run()


if __name__ == "__main__":
    try:
        print(json.dumps(dict(ok=True, result=main()), ensure_ascii=False))
    except Exception as exc:
        print(json.dumps(dict(ok=False, error=str(exc)), ensure_ascii=False))
        sys.exit(1)
