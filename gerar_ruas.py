#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera os pacotes de ruas do app "Mandados do dia" a partir do CNEFE do IBGE (Censo 2022).

Para cada cidade pedida, cria  ruas/<codigo IBGE>.json  (ruas com alguns pontos cada e,
quando o CEP identifica bem um trecho, o ponto médio do CEP) e atualiza  ruas/indice.json.
Os arquivos têm só nomes de ruas e coordenadas: nenhum dado de parte ou de mandado.

Uso (o GitHub roda isto sozinho; no computador também funciona):
    python gerar_ruas.py --cidades "Foz do Iguaçu/PR; Santa Terezinha de Itaipu/PR"

Opções úteis:
    --saida PASTA          onde gravar (padrão: ruas)
    --pasta-zips PASTA     usa arquivos .zip/.csv do CNEFE já baixados nesta pasta (sem internet)
    --municipios ARQUIVO   lista de municípios (JSON da API do IBGE) em vez de consultar a internet
    --base-url URL         endereço da pasta CSV do CNEFE no FTP do IBGE
Fonte dos dados: IBGE, Censo Demográfico 2022, Cadastro Nacional de Endereços para Fins Estatísticos (CNEFE).
"""
import argparse, csv, io, json, math, os, re, sys, tempfile, time, unicodedata, zipfile
import urllib.request, urllib.error
from collections import Counter, defaultdict
from html.parser import HTMLParser

BASE_PADRAO = ("https://ftp.ibge.gov.br/Cadastro_Nacional_de_Enderecos_para_Fins_Estatisticos/"
               "Censo_Demografico_2022/Arquivos_CNEFE/CSV/")
API_MUNICIPIOS = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
CELULA = 0.005          # ~550 m: ruas longas viram vários pontos (um por trecho)
MAX_PONTOS_RUA = 10
JUNTAR_KM = 0.35       # pontos da mesma rua mais perto que isto viram um só
RAIO_CEP_MAX_KM = 0.6   # CEP só entra se os endereços dele forem juntos (senão é "CEP da cidade inteira")
MIN_ENDERECOS_CEP = 3


UF_SIGLAS = {'11': 'RO', '12': 'AC', '13': 'AM', '14': 'RR', '15': 'PA', '16': 'AP', '17': 'TO', '21': 'MA', '22': 'PI',
             '23': 'CE', '24': 'RN', '25': 'PB', '26': 'PE', '27': 'AL', '28': 'SE', '29': 'BA', '31': 'MG', '32': 'ES',
             '33': 'RJ', '35': 'SP', '41': 'PR', '42': 'SC', '43': 'RS', '50': 'MS', '51': 'MT', '52': 'GO', '53': 'DF'}


def sem_acento(t):
    return ''.join(c for c in unicodedata.normalize('NFD', str(t or '')) if unicodedata.category(c) != 'Mn')


def norm(t):
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9]+', ' ', sem_acento(t).lower())).strip()


def abrir_url(url, tentativas=2, binario=False, espera=25):
    ult = None
    for k in range(tentativas):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'mandados-do-dia-gerador/1.0'})
            with urllib.request.urlopen(req, timeout=espera) as r:
                return r.read() if binario else r.read().decode('utf-8', 'replace')
        except Exception as e:  # noqa
            ult = e
            time.sleep(2 * (k + 1))
    raise RuntimeError('Não consegui abrir %s (%s)' % (url, ult))


# ---------------------------------------------------------------- municípios (código IBGE)
def carregar_municipios(arquivo=None, tolerante=True, log=print):
    """Lista de municípios (IBGE). Se o site do IBGE não responder, devolve [] (o programa segue pelos arquivos locais)."""
    try:
        texto = open(arquivo, encoding='utf-8').read() if arquivo else abrir_url(API_MUNICIPIOS)
        dados = json.loads(texto)
    except Exception as e:  # noqa
        if not tolerante:
            raise
        log('(aviso) Não consegui a lista de municípios do IBGE: %s' % e)
        return []
    out = []
    for m in dados:
        try:
            uf = m['microrregiao']['mesorregiao']['UF']['sigla']
        except Exception:
            try:
                uf = m['regiao-imediata']['regiao-intermediaria']['UF']['sigla']
            except Exception:
                uf = m.get('uf') or m.get('u') or ''
        out.append({'c': str(m['id']), 'n': m['nome'], 'u': uf})
    return out


def cidade_com_codigo(texto):
    """'4108304=Foz do Iguaçu/PR' -> município sem precisar de internet."""
    m = re.match(r'^\s*(\d{7})\s*=\s*(.+?)\s*(?:[/\-]\s*([A-Za-z]{2}))?\s*$', texto)
    if not m:
        return None
    cod, nome, uf = m.group(1), m.group(2).strip(), (m.group(3) or '').upper()
    return {'c': cod, 'n': nome, 'u': uf or UF_SIGLAS.get(cod[:2], '')}


def cidade_pelo_arquivo(texto, pasta):
    """Sem lista do IBGE: acha o arquivo cujo nome tem o código e o nome da cidade (ex.: 4108304_FOZ_DO_IGUACU.zip)."""
    if not pasta or not os.path.isdir(pasta):
        return None
    nome, uf = texto.strip(), ''
    m = re.match(r'^(.*?)\s*[/\-]\s*([A-Za-z]{2})\s*$', nome)
    if m:
        nome, uf = m.group(1), m.group(2).upper()
    alvo = norm(nome)
    for raiz, _, arqs in os.walk(pasta):
        for a in sorted(arqs):
            mm = re.match(r'^(\d{7})[_\-\s]*(.*?)\.(zip|csv)$', a, re.I)
            if mm and mm.group(2) and norm(mm.group(2).replace('_', ' ')) == alvo:
                cod = mm.group(1)
                return {'c': cod, 'n': nome.strip(), 'u': uf or UF_SIGLAS.get(cod[:2], '')}
    return None


def achar_cidade(texto, municipios):
    """'Foz do Iguaçu/PR' (ou só o nome) -> município. Erra com mensagem clara se não achar ou se houver dúvida."""
    nome, uf = texto, ''
    m = re.match(r'^(.*?)\s*[/\-]\s*([A-Za-z]{2})\s*$', texto.strip())
    if m:
        nome, uf = m.group(1), m.group(2).upper()
    nn = norm(nome)
    achados = [x for x in municipios if norm(x['n']) == nn and (not uf or x['u'].upper() == uf)]
    if not achados:
        raise ValueError('Cidade não encontrada: "%s". Confira o nome e a sigla do estado (ex.: Foz do Iguaçu/PR).' % texto.strip())
    if len(achados) > 1:
        raise ValueError('Mais de uma cidade com o nome "%s". Escreva com a sigla do estado, por exemplo: %s' %
                         (texto.strip(), '; '.join('%s/%s' % (x['n'], x['u']) for x in achados[:6])))
    return achados[0]


# ---------------------------------------------------------------- achar o arquivo do município no FTP do IBGE
class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for k, v in attrs:
                if k == 'href' and v:
                    self.links.append(v)


def listar(url):
    p = _Links()
    p.feed(abrir_url(url))
    out = []
    for h in p.links:
        if h.startswith(('?', '#', '/', 'http')) or h.startswith('..'):
            continue
        out.append(h)
    return out


def achar_arquivo(cod, base, log=print):
    """Procura no índice do FTP um arquivo do município (7 dígitos); se não houver, um arquivo da UF (2 dígitos)."""
    uf2 = cod[:2]
    visitados, fila, uf_arquivos = set(), [(base, 0)], []
    while fila:
        url, prof = fila.pop(0)
        if url in visitados or prof > 3:
            continue
        visitados.add(url)
        try:
            itens = listar(url)
        except Exception as e:  # noqa
            log('  (não consegui listar %s: %s)' % (url, e))
            continue
        pastas = [h for h in itens if h.endswith('/')]
        arqs = [h for h in itens if not h.endswith('/')]
        for a in arqs:
            nome = urllib.request.unquote(a).lower()
            if nome.endswith(('.zip', '.csv')):
                if nome.startswith(cod):
                    return url + a
                if nome.startswith(uf2 + '_') or nome.startswith(uf2 + '-'):
                    uf_arquivos.append(url + a)
        # primeiro as pastas que parecem "Municipio" e a da UF; depois as demais
        def prio(h):
            n = urllib.request.unquote(h).lower()
            return (0 if 'municip' in n else (1 if n.startswith(uf2) else 2), n)
        for h in sorted(pastas, key=prio):
            n = urllib.request.unquote(h).lower()
            if prof >= 1 and 'municip' not in url.lower() and not n.startswith(uf2) and 'municip' not in n:
                continue
            fila.append((url + h, prof + 1))
    if uf_arquivos:
        log('  arquivo do município não achado; vou filtrar o arquivo da UF: %s' % uf_arquivos[0])
        return uf_arquivos[0]
    raise RuntimeError('Não achei o arquivo do CNEFE do município %s em %s' % (cod, base))


def baixar(url, destino, log=print):
    log('  baixando %s' % url)
    req = urllib.request.Request(url, headers={'User-Agent': 'mandados-do-dia-gerador/1.0'})
    with urllib.request.urlopen(req, timeout=300) as r, open(destino, 'wb') as f:
        while True:
            b = r.read(1 << 20)
            if not b:
                break
            f.write(b)


# ---------------------------------------------------------------- leitura do CSV do CNEFE
def abrir_csv(caminho):
    """Devolve (iterador de linhas de texto, fechar). Aceita .csv ou .zip (primeiro .csv de dentro)."""
    if caminho.lower().endswith('.zip'):
        z = zipfile.ZipFile(caminho)
        nomes = [n for n in z.namelist() if n.lower().endswith('.csv')]
        if not nomes:
            raise RuntimeError('O .zip não tem arquivo .csv dentro: %s' % caminho)
        bruto = z.open(nomes[0])
        fechar = lambda: (bruto.close(), z.close())  # noqa
    else:
        bruto = open(caminho, 'rb')
        fechar = bruto.close
    amostra = bruto.read(65536)
    try:
        amostra.decode('utf-8')
        cod = 'utf-8-sig'
    except UnicodeDecodeError:
        cod = 'latin-1'
    if caminho.lower().endswith('.zip'):
        bruto.close()
        z2 = zipfile.ZipFile(caminho)
        bruto = z2.open(nomes[0])
        fechar = lambda: (bruto.close(), z2.close())  # noqa
    else:
        bruto.seek(0)
    return io.TextIOWrapper(bruto, encoding=cod, newline=''), fechar


def num(t):
    t = str(t or '').strip()
    if not t:
        return None
    if ',' in t and '.' not in t:
        t = t.replace(',', '.')
    try:
        return float(t)
    except ValueError:
        return None


def km(lat1, lng1, lat2, lng2):
    x = (lng2 - lng1) * math.cos(math.radians((lat1 + lat2) / 2))
    y = lat2 - lat1
    return math.hypot(x, y) * 111.32


def processar(linhas, cod_municipio=None, log=print):
    """Lê as linhas do CSV e devolve (ruas, ceps) já agregados."""
    leitor = csv.DictReader(linhas, delimiter=';')
    campos = {c.strip().upper(): c for c in (leitor.fieldnames or [])}
    for obrig in ('NOM_SEGLOGR', 'LATITUDE', 'LONGITUDE'):
        if obrig not in campos:
            raise RuntimeError('O arquivo não tem a coluna %s (colunas achadas: %s)' % (obrig, ', '.join(list(campos)[:12])))
    g = lambda r, k: (r.get(campos[k]) or '').strip() if k in campos else ''  # noqa
    ruas = {}      # chave -> {'nomes': Counter, 'cel': {(i,j): [n, soma_lat, soma_lng]}}
    ceps = {}      # cep -> [n, sx, sy, sxx, syy]
    lidas = usadas = 0
    for r in leitor:
        lidas += 1
        if cod_municipio and campos.get('COD_MUNICIPIO') and g(r, 'COD_MUNICIPIO') != cod_municipio:
            continue
        lat, lng = num(g(r, 'LATITUDE')), num(g(r, 'LONGITUDE'))
        if lat is None or lng is None or not (-34 <= lat <= 6 and -74 <= lng <= -34):
            continue
        nome = ' '.join(x for x in (g(r, 'NOM_TIPO_SEGLOGR'), g(r, 'NOM_TITULO_SEGLOGR'), g(r, 'NOM_SEGLOGR')) if x)
        cep = re.sub(r'\D', '', g(r, 'CEP'))
        if len(cep) == 8:
            c = ceps.setdefault(cep, [0, 0.0, 0.0, 0.0, 0.0])
            c[0] += 1; c[1] += lat; c[2] += lng; c[3] += lat * lat; c[4] += lng * lng
        if not g(r, 'NOM_SEGLOGR'):
            continue
        chave = norm(nome)
        if not chave:
            continue
        usadas += 1
        d = ruas.setdefault(chave, {'nomes': Counter(), 'cel': {}})
        d['nomes'][nome.upper()] += 1
        cel = (math.floor(lat / CELULA), math.floor(lng / CELULA))
        a = d['cel'].setdefault(cel, [0, 0.0, 0.0])
        a[0] += 1; a[1] += lat; a[2] += lng
    log('  %d linhas lidas, %d endereços com rua e coordenada, %d ruas' % (lidas, usadas, len(ruas)))
    return ruas, ceps


def montar_pacote(cidade, ruas, ceps):
    pontos_ruas = {}
    todos = []
    for chave, d in ruas.items():
        nome = d['nomes'].most_common(1)[0][0]
        cels = sorted(d['cel'].values(), key=lambda a: -a[0])
        pts = []
        for a in cels:                      # junta trechos vizinhos (divisa de células) e limita o total
            q = (a[1] / a[0], a[2] / a[0])
            if all(km(q[0], q[1], k[0], k[1]) > JUNTAR_KM for k in pts):
                pts.append(q)
            if len(pts) >= MAX_PONTOS_RUA:
                break
        pontos_ruas[nome] = pts
        todos.extend(pts)
    pontos_cep = {}
    for cep, (n, sx, sy, sxx, syy) in ceps.items():
        if n < MIN_ENDERECOS_CEP:
            continue
        mx, my = sx / n, sy / n
        var_x, var_y = max(sxx / n - mx * mx, 0), max(syy / n - my * my, 0)
        raio = (math.sqrt(var_x) * 111.32) + (math.sqrt(var_y) * 111.32 * math.cos(math.radians(mx)))
        if raio <= RAIO_CEP_MAX_KM:
            pontos_cep[cep] = (mx, my)
            todos.append((mx, my))
    if not todos:
        raise RuntimeError('Nenhuma rua com coordenada válida em %s' % cidade['n'])
    b0 = round(min(p[0] for p in todos) - 0.01, 2)
    b1 = round(min(p[1] for p in todos) - 0.01, 2)
    enc = lambda p: '%d %d' % (round((p[0] - b0) * 1e5), round((p[1] - b1) * 1e5))  # noqa
    r = '|'.join('%s=%s' % (nome.replace('|', ' ').replace('=', ' '), ';'.join(enc(p) for p in pts))
                 for nome, pts in sorted(pontos_ruas.items()))
    p = '|'.join('%s=%s' % (cep, enc(pt)) for cep, pt in sorted(pontos_cep.items()))
    return {'v': 1, 'c': cidade['c'], 'n': cidade['n'], 'u': cidade['u'],
            'f': 'IBGE, Censo Demográfico 2022, CNEFE', 't': time.strftime('%Y-%m-%d'),
            'b': [b0, b1], 'r': r, 'p': p}, len(pontos_ruas), len(pontos_cep)


def gravar(saida, cidade, pacote, n_ruas, n_ceps):
    os.makedirs(saida, exist_ok=True)
    caminho = os.path.join(saida, cidade['c'] + '.json')
    texto = json.dumps(pacote, ensure_ascii=False, separators=(',', ':'))
    with open(caminho, 'w', encoding='utf-8') as f:
        f.write(texto)
    idx_path = os.path.join(saida, 'indice.json')
    try:
        idx = json.load(open(idx_path, encoding='utf-8'))
    except Exception:
        idx = {'v': 1, 'cidades': []}
    idx['cidades'] = [x for x in idx.get('cidades', []) if x.get('c') != cidade['c']]
    idx['cidades'].append({'c': cidade['c'], 'n': cidade['n'], 'u': cidade['u'], 't': pacote['t'],
                           'r': n_ruas, 'p': n_ceps, 'b': len(texto.encode('utf-8'))})
    idx['cidades'].sort(key=lambda x: (x['u'], x['n']))
    with open(idx_path, 'w', encoding='utf-8') as f:
        json.dump(idx, f, ensure_ascii=False, separators=(',', ':'))
    return caminho, len(texto.encode('utf-8'))


def achar_local(pasta, cod):
    for raiz, _, arqs in os.walk(pasta):
        for a in sorted(arqs):
            n = a.lower()
            if n.endswith(('.zip', '.csv')) and (n.startswith(cod) or cod in n):
                return os.path.join(raiz, a)
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description='Gera pacotes de ruas por município (CNEFE/IBGE).')
    ap.add_argument('--cidades', required=True, help='Ex.: "Foz do Iguaçu/PR; Santa Terezinha de Itaipu/PR"')
    ap.add_argument('--saida', default='ruas')
    ap.add_argument('--pasta-zips', default=None)
    ap.add_argument('--municipios', default=None)
    ap.add_argument('--base-url', default=BASE_PADRAO)
    a = ap.parse_args(argv)
    pedidas = [x.strip() for x in re.split(r'[;\n]', a.cidades) if x.strip()]
    if not pedidas:
        print('Nenhuma cidade informada.'); return 2
    pasta = a.pasta_zips or ('cnefe' if os.path.isdir('cnefe') else None)
    municipios = carregar_municipios(a.municipios)
    erros = []
    for texto in pedidas:
        print('== %s' % texto)
        try:
            cid = cidade_com_codigo(texto)
            if not cid and municipios:
                try:
                    cid = achar_cidade(texto, municipios)
                except ValueError:
                    cid = cidade_pelo_arquivo(texto, pasta)
                    if not cid:
                        raise
            if not cid:
                cid = cidade_pelo_arquivo(texto, pasta)
            if not cid:
                raise ValueError('Não consegui identificar a cidade "%s" sem a lista do IBGE. Escreva com o código do IBGE, por exemplo: 4108304=Foz do Iguaçu/PR (o código são os 7 números no começo do nome do arquivo baixado).' % texto.strip())
            print('  município: %s/%s (código %s)' % (cid['n'], cid['u'], cid['c']))
            caminho = achar_local(pasta, cid['c']) if pasta else None
            tmp = None
            if not caminho:
                try:
                    url = achar_arquivo(cid['c'], a.base_url)
                except Exception as e:  # noqa
                    raise RuntimeError('Não achei o arquivo do CNEFE de %s na pasta "cnefe" do repositório e o site do IBGE não responde a partir do GitHub (%s). Baixe o arquivo da cidade pelo celular e suba na pasta "cnefe" (veja o LEIA-ME-RUAS).' % (cid['n'], e))
                tmp = tempfile.mkdtemp()
                caminho = os.path.join(tmp, os.path.basename(urllib.request.unquote(url)) or (cid['c'] + '.zip'))
                baixar(url, caminho)
            linhas, fechar = abrir_csv(caminho)
            try:
                ruas, ceps = processar(linhas, cid['c'])
            finally:
                fechar()
            pacote, nr, nc = montar_pacote(cid, ruas, ceps)
            cam, tam = gravar(a.saida, cid, pacote, nr, nc)
            print('  OK: %s (%d ruas, %d CEPs com ponto, %.0f KB)' % (cam, nr, nc, tam / 1024))
        except Exception as e:  # noqa
            print('  ERRO: %s' % e)
            erros.append('%s: %s' % (texto, e))
    if erros:
        print('\nProblemas:\n- ' + '\n- '.join(erros))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
