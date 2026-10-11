#!/usr/bin/env python3
"""
Script de Submissão IndexNow para Calculadora da Sorte
Protocolo IndexNow (Bing, Yandex, Seznam, Naver, etc.)

Uso:
    python scripts/submit_indexnow.py
    python scripts/submit_indexnow.py --dry-run
    python scripts/submit_indexnow.py --limit 10
    python scripts/submit_indexnow.py --url https://www.calculodasorte.com.br/lotofacil
"""

import os
import sys
import json
import re
import argparse
import urllib.request
import urllib.error
from urllib.parse import urlparse

DEFAULT_HOST = "www.calculodasorte.com.br"
DEFAULT_KEY = "8473a2b1c9f4d5e68473a2b1c9f4d5e6"
DEFAULT_ENDPOINT = "https://api.indexnow.org/indexnow"
DEFAULT_BATCH_SIZE = 1000


def extract_urls_from_xml(xml_text: str) -> list[str]:
    pattern = re.compile(r"<loc>\s*(https?://[^<\s]+)\s*</loc>", re.IGNORECASE)
    return pattern.findall(xml_text)


def fetch_xml(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "CalculadoraDaSorte-IndexNow/1.0 (+https://www.calculodasorte.com.br)",
            "Accept": "application/xml, text/xml, */*",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def discover_urls_from_sitemaps(sitemap_index_url: str, expected_host: str) -> list[str]:
    print(f"[IndexNow] Coletando URLs a partir do sitemap: {sitemap_index_url}")
    root_xml = fetch_xml(sitemap_index_url)

    is_index = "<sitemapindex" in root_xml.lower()
    collected_urls = set()

    if is_index:
        sub_sitemaps = extract_urls_from_xml(root_xml)
        print(f"[IndexNow] Identificado Sitemap Index com {len(sub_sitemaps)} sub-sitemaps.")

        for sub_url in sub_sitemaps:
            try:
                sub_xml = fetch_xml(sub_url)
                urls = extract_urls_from_xml(sub_xml)
                valid_count = 0
                for u in urls:
                    try:
                        parsed = urlparse(u)
                        if parsed.netloc == expected_host:
                            collected_urls.add(u)
                            valid_count += 1
                    except Exception:
                        pass
                print(f"  [OK] {sub_url} ({valid_count} URLs válidas)")
            except Exception as err:
                print(f"  [ERRO] Falha ao ler sub-sitemap {sub_url}: {err}", file=sys.stderr)
    else:
        urls = extract_urls_from_xml(root_xml)
        for u in urls:
            try:
                parsed = urlparse(u)
                if parsed.netloc == expected_host:
                    collected_urls.add(u)
            except Exception:
                pass

    return sorted(list(collected_urls))


def chunk_list(items: list, size: int) -> list[list]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def submit_batch_to_indexnow(
    endpoint: str,
    host: str,
    key: str,
    key_location: str,
    batch: list[str],
    batch_index: int,
    total_batches: int,
) -> bool:
    payload = {
        "host": host,
        "key": key,
        "keyLocation": key_location,
        "urlList": batch,
    }
    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        endpoint,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = resp.status
            if status in (200, 202):
                print(
                    f"[IndexNow] Lote {batch_index}/{total_batches} ({len(batch)} URLs): Sucesso (HTTP {status})"
                )
                return True
            else:
                print(
                    f"[IndexNow] Lote {batch_index}/{total_batches} ({len(batch)} URLs): Status inesperado (HTTP {status})",
                    file=sys.stderr,
                )
                return False
    except urllib.error.HTTPError as err:
        err_body = err.read().decode("utf-8", errors="replace")
        print(
            f"[IndexNow] Lote {batch_index}/{total_batches} ({len(batch)} URLs): FALHOU (HTTP {err.code})",
            file=sys.stderr,
        )
        if err_body:
            print(f"  Detalhes: {err_body}", file=sys.stderr)
        return False
    except Exception as err:
        print(
            f"[IndexNow] Lote {batch_index}/{total_batches} ({len(batch)} URLs): Erro de conexão: {err}",
            file=sys.stderr,
        )
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Submete URLs do Cálculo da Sorte ao protocolo IndexNow."
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Simula a execução sem enviar à API",
    )
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=None,
        help="Limita a submissão aos primeiros N links",
    )
    parser.add_argument(
        "--batch-size",
        "-b",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Tamanho do lote por requisição (padrão: {DEFAULT_BATCH_SIZE})",
    )
    parser.add_argument(
        "--url",
        "-u",
        dest="single_url",
        default=None,
        help="Submete uma única URL específica",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("INDEXNOW_HOST", DEFAULT_HOST),
        help=f"Host alvo (padrão: {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--key",
        default=os.environ.get("INDEXNOW_KEY", DEFAULT_KEY),
        help="Chave IndexNow",
    )
    parser.add_argument(
        "--sitemap",
        dest="sitemap_url",
        default=None,
        help="URL do sitemap.xml principal",
    )

    args = parser.parse_args()

    host = args.host
    key = args.key
    key_location = os.environ.get("INDEXNOW_KEY_LOCATION", f"https://{host}/{key}.txt")
    endpoint = os.environ.get("INDEXNOW_ENDPOINT", DEFAULT_ENDPOINT)
    sitemap_url = args.sitemap_url or os.environ.get(
        "SITEMAP_URL", f"https://{host}/sitemap.xml"
    )

    print("=" * 60)
    print("  Calculadora da Sorte - Submissão IndexNow (Python)")
    print("=" * 60)
    print(f"Host:         {host}")
    print(f"Key Location: {key_location}")
    print(f"Endpoint:     {endpoint}")
    print(f"Modo:         {'DRY RUN (Simulação)' if args.dry_run else 'PRODUÇÃO (Envio Real)'}")
    print("=" * 60)

    if args.single_url:
        urls = [args.single_url]
        print(f"[IndexNow] Submissão direcionada de URL única: {args.single_url}")
    else:
        try:
            urls = discover_urls_from_sitemaps(sitemap_url, host)
        except Exception as err:
            print(f"[IndexNow] Erro ao consultar sitemap remoto ({sitemap_url}): {err}", file=sys.stderr)
            sys.exit(1)

    if not urls:
        print("[IndexNow] Nenhuma URL encontrada para submissão.")
        sys.exit(0)

    if args.limit and args.limit > 0 and len(urls) > args.limit:
        print(f"[IndexNow] Limitando lista às primeiras {args.limit} URLs (de {len(urls)}).")
        urls = urls[: args.limit]

    print(f"[IndexNow] Total de URLs a submeter: {len(urls)}")

    batch_size = max(1, min(args.batch_size, 10000))
    batches = chunk_list(urls, batch_size)
    print(f"[IndexNow] Dividido em {len(batches)} lote(s) de até {batch_size} URLs.")

    if args.dry_run:
        print("\n[IndexNow] Modo Dry-run ativado. Exibindo amostra das primeiras 5 URLs:")
        for i, u in enumerate(urls[:5]):
            print(f"  {i + 1}. {u}")
        print(f"\n[IndexNow] Simulação concluída com sucesso ({len(urls)} URLs válidas em {len(batches)} lotes).")
        sys.exit(0)

    failures = 0
    for idx, batch in enumerate(batches, 1):
        success = submit_batch_to_indexnow(
            endpoint=endpoint,
            host=host,
            key=key,
            key_location=key_location,
            batch=batch,
            batch_index=idx,
            total_batches=len(batches),
        )
        if not success:
            failures += 1

    print("=" * 60)
    if failures == 0:
        print(f"[IndexNow] Concluído com sucesso! {len(urls)} URLs enviadas ao Bing/IndexNow.")
        sys.exit(0)
    else:
        print(f"[IndexNow] Finalizado com {failures} lote(s) com erro.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
