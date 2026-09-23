"""Shared source downloads; paths and source registries are caller-owned."""
import pathlib
import subprocess

def curl(url, out):
    subprocess.run(["curl", "-sL", "--fail", url, "-o", str(out)], check=True)


def prefetch_pools(tsv_path):
    """Fetch pools with curl up front (urllib SSL is broken on this python)."""
    tsv_path = pathlib.Path(tsv_path)
    cache = tsv_path.parent / "deckcache"
    cache.mkdir(exist_ok=True)
    for line in tsv_path.read_text().splitlines()[1:]:
        if not line.strip():
            continue
        pool_id = line.split("\t")[3].rstrip("/").split("/")[-1]
        path = cache / f"{pool_id}.json"
        if not path.exists():
            curl(f"https://sealeddeck.tech/api/pools/{pool_id}", path)
            print(f"fetched pool {pool_id}")
