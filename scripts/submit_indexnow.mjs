#!/usr/bin/env node

/**
 * Script de Submissão IndexNow para Calculadora da Sorte
 * Protocolo IndexNow (Bing, Yandex, Seznam, Naver, etc.)
 *
 * Uso:
 *   npm run indexnow:submit
 *   npm run indexnow:submit -- --dry-run
 *   npm run indexnow:submit -- --limit 10
 *   npm run indexnow:submit -- --url https://www.calculodasorte.com.br/lotofacil
 */

import { argv, env, exit } from 'node:process';

const DEFAULT_HOST = 'www.calculodasorte.com.br';
const DEFAULT_KEY = '8473a2b1c9f4d5e68473a2b1c9f4d5e6';
const DEFAULT_ENDPOINT = 'https://api.indexnow.org/indexnow';
const DEFAULT_BATCH_SIZE = 1000;

function parseArgs() {
  const args = argv.slice(2);
  const options = {
    dryRun: false,
    limit: null,
    batchSize: DEFAULT_BATCH_SIZE,
    singleUrl: null,
    host: env.INDEXNOW_HOST || DEFAULT_HOST,
    key: env.INDEXNOW_KEY || DEFAULT_KEY,
    sitemapUrl: env.SITEMAP_URL || `https://${env.INDEXNOW_HOST || DEFAULT_HOST}/sitemap.xml`,
    endpoint: env.INDEXNOW_ENDPOINT || DEFAULT_ENDPOINT,
  };

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === '--dry-run' || arg === '-n') {
      options.dryRun = true;
    } else if (arg === '--limit' || arg === '-l') {
      options.limit = parseInt(args[++i], 10);
    } else if (arg === '--batch-size' || arg === '-b') {
      options.batchSize = parseInt(args[++i], 10);
    } else if (arg === '--url' || arg === '-u') {
      options.singleUrl = args[++i];
    } else if (arg === '--host') {
      options.host = args[++i];
    } else if (arg === '--key') {
      options.key = args[++i];
    } else if (arg === '--sitemap') {
      options.sitemapUrl = args[++i];
    } else if (arg === '--help' || arg === '-h') {
      console.log(`
Uso: npm run indexnow:submit [opções]

Opções:
  --dry-run, -n         Simula a execução sem enviar requisições à API
  --limit, -l <n>       Limita a submissão aos primeiros N links
  --batch-size, -b <n>  Tamanho do lote por requisição (padrão: 1000, máx: 10000)
  --url, -u <url>       Submete uma única URL específica
  --host <host>         Host personalizado (padrão: ${DEFAULT_HOST})
  --key <key>           Chave IndexNow personalizada
  --sitemap <url>       URL do sitemap.xml principal
  --help, -h            Exibe esta ajuda
      `);
      exit(0);
    }
  }

  options.keyLocation = env.INDEXNOW_KEY_LOCATION || `https://${options.host}/${options.key}.txt`;
  return options;
}

function extractUrlsFromXml(xmlText) {
  const locRegex = /<loc>\s*([^<\s]+)\s*<\/loc>/gi;
  const urls = [];
  let match;
  while ((match = locRegex.exec(xmlText)) !== null) {
    const url = match[1].trim();
    if (url.startsWith('http://') || url.startsWith('https://')) {
      urls.push(url);
    }
  }
  return urls;
}

async function fetchXml(url) {
  const res = await fetch(url, {
    headers: {
      'User-Agent': 'CalculadoraDaSorte-IndexNow/1.0 (+https://www.calculodasorte.com.br)',
      'Accept': 'application/xml, text/xml, */*',
    },
  });

  if (!res.ok) {
    throw new Error(`HTTP ${res.status} ao acessar ${url}`);
  }

  return await res.text();
}

async function discoverUrlsFromSitemaps(sitemapIndexUrl, expectedHost) {
  console.log(`[IndexNow] Coletando URLs a partir do sitemap: ${sitemapIndexUrl}`);
  const rootXml = await fetchXml(sitemapIndexUrl);

  const isIndex = /<sitemapindex/i.test(rootXml);
  const collectedUrls = new Set();

  if (isIndex) {
    const subSitemaps = extractUrlsFromXml(rootXml);
    console.log(`[IndexNow] Identificado Sitemap Index com ${subSitemaps.length} sub-sitemaps.`);

    for (const subUrl of subSitemaps) {
      try {
        const subXml = await fetchXml(subUrl);
        const urls = extractUrlsFromXml(subXml);
        for (const u of urls) {
          try {
            const parsed = new URL(u);
            if (parsed.hostname === expectedHost) {
              collectedUrls.add(u);
            }
          } catch {
            // Ignora URL inválida
          }
        }
        console.log(`  [OK] ${subUrl} (${urls.length} URLs)`);
      } catch (err) {
        console.warn(`  [ERRO] Falha ao ler sub-sitemap ${subUrl}: ${err.message}`);
      }
    }
  } else {
    const urls = extractUrlsFromXml(rootXml);
    for (const u of urls) {
      try {
        const parsed = new URL(u);
        if (parsed.hostname === expectedHost) {
          collectedUrls.add(u);
        }
      } catch {
        // Ignora URL inválida
      }
    }
  }

  return Array.from(collectedUrls);
}

function chunkArray(array, size) {
  const chunks = [];
  for (let i = 0; i < array.length; i += size) {
    chunks.push(array.slice(i, i + size));
  }
  return chunks;
}

async function submitBatchToIndexNow(options, batch, batchIndex, totalBatches) {
  const payload = {
    host: options.host,
    key: options.key,
    keyLocation: options.keyLocation,
    urlList: batch,
  };

  const res = await fetch(options.endpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
    },
    body: JSON.stringify(payload),
  });

  const responseText = await res.text().catch(() => '');
  const isSuccess = res.status === 200 || res.status === 202;

  if (isSuccess) {
    console.log(`[IndexNow] Lote ${batchIndex}/${totalBatches} (${batch.length} URLs): Sucesso (HTTP ${res.status})`);
    return { ok: true, status: res.status };
  } else {
    console.error(`[IndexNow] Lote ${batchIndex}/${totalBatches} (${batch.length} URLs): FALHOU (HTTP ${res.status})`);
    if (responseText) {
      console.error(`  Detalhes: ${responseText}`);
    }
    return { ok: false, status: res.status, error: responseText };
  }
}

async function main() {
  const options = parseArgs();

  console.log('='.repeat(60));
  console.log('  Calculadora da Sorte - Submissão IndexNow');
  console.log('='.repeat(60));
  console.log(`Host:         ${options.host}`);
  console.log(`Key Location: ${options.keyLocation}`);
  console.log(`Endpoint:     ${options.endpoint}`);
  console.log(`Modo:         ${options.dryRun ? 'DRY RUN (Simulação)' : 'PRODUÇÃO (Envio Real)'}`);
  console.log('='.repeat(60));

  let urls = [];

  if (options.singleUrl) {
    urls = [options.singleUrl];
    console.log(`[IndexNow] Submissão direcionada de URL única: ${options.singleUrl}`);
  } else {
    try {
      urls = await discoverUrlsFromSitemaps(options.sitemapUrl, options.host);
    } catch (err) {
      console.error(`[IndexNow] Erro ao consultar sitemap remoto (${options.sitemapUrl}): ${err.message}`);
      console.log('[IndexNow] Abortando submissão. Verifique a conexão ou use --url para submissão manual.');
      exit(1);
    }
  }

  if (urls.length === 0) {
    console.warn('[IndexNow] Nenhuma URL encontrada para submissão.');
    exit(0);
  }

  if (options.limit && options.limit > 0 && urls.length > options.limit) {
    console.log(`[IndexNow] Limitando lista às primeiras ${options.limit} URLs (de ${urls.length}).`);
    urls = urls.slice(0, options.limit);
  }

  console.log(`[IndexNow] Total de URLs a submeter: ${urls.length}`);

  const batches = chunkArray(urls, Math.min(Math.max(options.batchSize, 1), 10000));
  console.log(`[IndexNow] Dividido em ${batches.length} lote(s) de até ${options.batchSize} URLs.`);

  if (options.dryRun) {
    console.log('\n[IndexNow] Modo Dry-run ativado. Exibindo amostra das primeiras 5 URLs:');
    urls.slice(0, 5).forEach((u, i) => console.log(`  ${i + 1}. ${u}`));
    console.log(`\n[IndexNow] Simulação concluída com sucesso (${urls.length} URLs válidas em ${batches.length} lotes).`);
    exit(0);
  }

  let failures = 0;
  for (let i = 0; i < batches.length; i++) {
    const result = await submitBatchToIndexNow(options, batches[i], i + 1, batches.length);
    if (!result.ok) {
      failures++;
    }
  }

  console.log('='.repeat(60));
  if (failures === 0) {
    console.log(`[IndexNow] Concluído com sucesso! ${urls.length} URLs enviadas ao Bing/IndexNow.`);
    exit(0);
  } else {
    console.error(`[IndexNow] Finalizado com ${failures} lote(s) com erro.`);
    exit(1);
  }
}

main().catch((err) => {
  console.error('[IndexNow] Erro fatal:', err);
  exit(1);
});
