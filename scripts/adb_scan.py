#!/usr/bin/env python3
"""
adb_scan.py — Captura automática de Pokémon GO via ADB.

O script conecta no celular via USB, detecta quando a tela de detalhe de um
Pokémon está aberta e envia o screenshot para o MeuPokémonGO processar via OCR.
Quando você terminar, acesse /scan/preview para revisar e confirmar.

Pré-requisitos
--------------
  pip install Pillow requests
  ADB instalado e no PATH (Android Platform Tools)
  USB Debugging ativado no celular (Config. do Desenvolvedor)

Uso
---
  python scripts/adb_scan.py --url https://meupokemongo.duckdns.org \\
         --user felipe --password SUASENHA

  # Intervalo menor (detecta mais rápido, mais CPU):
  python scripts/adb_scan.py ... --interval 1.5

  # Sem checar se o GO está em foreground (útil se o check travar):
  python scripts/adb_scan.py ... --no-go-check
"""

import argparse
import hashlib
import io
import re
import subprocess
import sys
import time

try:
    from PIL import Image
except ImportError:
    print("Pillow não encontrado. Execute: pip install Pillow requests")
    sys.exit(1)

try:
    import requests as req_lib
except ImportError:
    print("requests não encontrado. Execute: pip install Pillow requests")
    sys.exit(1)


# ── ANSI colors ────────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"


# ── ADB helpers ────────────────────────────────────────────────────────────────

def adb(*args, timeout=8) -> subprocess.CompletedProcess:
    return subprocess.run(["adb", *args], capture_output=True, timeout=timeout)


def screencap() -> bytes:
    r = adb("exec-out", "screencap", "-p", timeout=12)
    if r.returncode != 0 or not r.stdout:
        raise RuntimeError(r.stderr.decode(errors="replace") or "screencap vazio")
    return r.stdout


def is_pokemon_go_foreground() -> bool:
    try:
        r = adb("shell", "dumpsys", "window", "windows", timeout=6)
        return b"com.nianticlabs.pokemongo" in r.stdout
    except Exception:
        return True  # assume sim se o check falhar


def notify_phone(name: str, cp) -> None:
    """Notificação no celular via ADB (Android 8+)."""
    try:
        msg = f"{name} · CP {cp}"
        adb("shell", "cmd", "notification", "post",
            "-S", "bigtext", "-t", "✅ Pokémon capturado!", "mpkm", msg,
            timeout=3)
    except Exception:
        pass  # notificação é bonus


# ── Detecção de tela ──────────────────────────────────────────────────────────

def screen_fingerprint(img_bytes: bytes) -> str:
    """Hash da região do nome (centro-alto). Muda a cada Pokémon novo."""
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    w, h = img.size
    region = img.crop((w // 4, int(h * 0.07), 3 * w // 4, int(h * 0.20)))
    small = region.resize((32, 8))
    return hashlib.md5(small.tobytes()).hexdigest()


def is_pokemon_detail(img_bytes: bytes) -> bool:
    """
    Heurística rápida: a tela de detalhe do Pokémon GO tem
    - fundo colorido saturado no topo (cor do tipo)
    - painel branco/claro na parte inferior (stats)
    """
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    w, h = img.size

    # Topo: checa saturação (gradiente do tipo)
    top = img.crop((0, 0, w, int(h * 0.38)))
    saturated = 0
    for r, g, b in top.getdata():
        mx = max(r, g, b)
        mn = min(r, g, b)
        if mx > 60 and (mx - mn) / mx > 0.22:
            saturated += 1
    sat_ratio = saturated / (top.width * top.height)

    # Inferior: checa presença de fundo claro (painel branco de stats)
    bottom = img.crop((0, int(h * 0.55), w, h))
    bright = sum(1 for r, g, b in bottom.getdata() if r > 195 and g > 195 and b > 195)
    bright_ratio = bright / (bottom.width * bottom.height)

    return sat_ratio > 0.12 and bright_ratio > 0.22


# ── Login no servidor ─────────────────────────────────────────────────────────

def login(base_url: str, username: str, password: str) -> req_lib.Session:
    sess = req_lib.Session()
    login_url = base_url.rstrip("/") + "/auth/login"

    # 1. Pega o CSRF token da página de login
    try:
        r = sess.get(login_url, timeout=12)
        r.raise_for_status()
    except Exception as e:
        print(f"{RED}❌ Não foi possível alcançar o servidor: {e}{RESET}")
        sys.exit(1)

    m = re.search(r'name="csrf_token"\s+value="([^"]+)"', r.text)
    if not m:
        print(f"{RED}❌ Token CSRF não encontrado na página de login. Verifique a URL.{RESET}")
        sys.exit(1)
    csrf_token = m.group(1)

    # 2. Faz login com as credenciais
    r = sess.post(login_url,
                  data={"username": username, "password": password, "csrf_token": csrf_token},
                  allow_redirects=True, timeout=12)

    if "Sair" in r.text or "logout" in r.text.lower() or r.url.rstrip("/").endswith("/"):
        return sess

    m_err = re.search(r'class="[^"]*(?:danger|error)[^"]*"[^>]*>\s*([^<]{5,})', r.text)
    err = m_err.group(1).strip() if m_err else "verifique usuário e senha"
    print(f"{RED}❌ Login falhou: {err}{RESET}")
    sys.exit(1)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="ADB Scan — captura automática de Pokémon GO",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--url", default="https://meupokemongo.duckdns.org",
                    help="URL do servidor MeuPokémonGO")
    ap.add_argument("--user", required=True, help="Nome de usuário")
    ap.add_argument("--password", required=True, help="Senha")
    ap.add_argument("--interval", type=float, default=1.8,
                    help="Intervalo entre verificações em segundos (padrão: 1.8)")
    ap.add_argument("--no-go-check", action="store_true",
                    help="Não verifica se o Pokémon GO está em foreground")
    args = ap.parse_args()

    base_url = args.url.rstrip("/")
    adb_url  = base_url + "/scan/adb"

    # ── Verifica ADB ──────────────────────────────────────────────────────────
    try:
        r = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5)
        devices = [l for l in r.stdout.splitlines() if "\tdevice" in l]
        if not devices:
            print(f"{RED}❌ Nenhum dispositivo ADB. Conecte o celular e ative USB Debugging.{RESET}")
            sys.exit(1)
        device_id = devices[0].split()[0]
    except FileNotFoundError:
        print(f"{RED}❌ ADB não encontrado. Instale o Android Platform Tools e adicione ao PATH.{RESET}")
        sys.exit(1)

    print(f"\n{BOLD}🎮 ADB Scan — MeuPokémonGO{RESET}")
    print(f"   📱 Dispositivo : {device_id}")
    print(f"   🌐 Servidor    : {base_url}")
    print(f"   ⏱️  Intervalo   : {args.interval}s")

    # ── Login ─────────────────────────────────────────────────────────────────
    print(f"\n   Fazendo login como {BOLD}{args.user}{RESET}...", end="", flush=True)
    sess = login(base_url, args.user, args.password)
    print(f" {GREEN}✓{RESET}")

    print(f"\n   Abra o {BOLD}Pokémon GO{RESET} e navegue pelos seus Pokémon.")
    print(f"   Pressione {BOLD}Ctrl+C{RESET} quando terminar — o script vai mostrar onde revisar.\n")

    last_fp  = None
    captured = 0
    skipped  = 0

    while True:
        try:
            if not args.no_go_check and not is_pokemon_go_foreground():
                print(f"\r{YELLOW}⏸  Aguardando Pokémon GO em foreground...{RESET}     ", end="", flush=True)
                time.sleep(2)
                continue

            try:
                img_bytes = screencap()
            except Exception as e:
                print(f"\r{RED}⚠️  screencap: {e}{RESET}" + " " * 20)
                time.sleep(2)
                continue

            fp = screen_fingerprint(img_bytes)

            if fp == last_fp:
                print(f"\r{CYAN}[{captured}✓] Aguardando próximo Pokémon...{RESET}     ", end="", flush=True)
                time.sleep(args.interval)
                continue

            if not is_pokemon_detail(img_bytes):
                print(f"\r{YELLOW}[{captured}✓] Tela sem Pokémon, ignorando...{RESET}     ", end="", flush=True)
                last_fp = fp
                time.sleep(args.interval)
                continue

            last_fp = fp
            print(f"\r📸 Enviando screenshot...                           ", end="", flush=True)

            try:
                resp = sess.post(
                    adb_url,
                    files={"file": ("screen.png", img_bytes, "image/png")},
                    timeout=25,
                )
            except Exception as e:
                print(f"\r{RED}⚠️  Erro de rede: {e}{RESET}" + " " * 20)
                time.sleep(args.interval)
                continue

            if resp.status_code == 401:
                print(f"\n{RED}❌ Sessão expirou. Reinicie o script para fazer login novamente.{RESET}")
                sys.exit(1)

            try:
                data = resp.json()
            except Exception:
                print(f"\r{RED}⚠️  Resposta inválida do servidor (HTTP {resp.status_code}){RESET}" + " " * 10)
                time.sleep(args.interval)
                continue

            if data.get("ok"):
                name = data.get("name", "?")
                cp   = str(data.get("cp") or "?")
                conf = data.get("confidence", 0)
                total = data.get("total", captured + 1)
                icon = (f"{GREEN}🟢{RESET}" if conf >= 0.85
                        else f"{YELLOW}🟡{RESET}" if conf >= 0.60
                        else f"{RED}🔴{RESET}")
                captured += 1
                print(f"\r{icon} #{total:03d} {BOLD}{name}{RESET} CP {cp}  (conf {conf:.0%})" + " " * 15)
                notify_phone(name, cp)
            else:
                reason = data.get("reason", "desconhecido")
                skipped += 1
                print(f"\r{YELLOW}⬜ Não reconhecido: {reason}{RESET}" + " " * 25)

            time.sleep(args.interval)

        except KeyboardInterrupt:
            print(f"\n\n{GREEN}{BOLD}✅ Sessão encerrada!{RESET}")
            print(f"   {GREEN}{captured}{RESET} Pokémon capturado{'s' if captured != 1 else ''}")
            if skipped:
                print(f"   {YELLOW}{skipped}{RESET} tela{'s' if skipped != 1 else ''} ignorada{'s' if skipped != 1 else ''}")
            if captured:
                print(f"\n   Acesse para revisar e confirmar:")
                print(f"   {CYAN}{BOLD}{base_url}/scan/preview{RESET}\n")
            sys.exit(0)
        except Exception as e:
            print(f"\r{RED}⚠️  {e}{RESET}" + " " * 30)
            time.sleep(2)


if __name__ == "__main__":
    main()
