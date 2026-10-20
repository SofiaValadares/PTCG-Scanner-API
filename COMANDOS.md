# Comandos

Tudo a partir da pasta `API-PTCG Scanner`. Se o PowerShell bloquear o script:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
```

| O quê | Script |
|---|---|
| Instalar venv + libs (só a 1ª vez) | `.\scripts\setup.ps1` |
| Subir a API neste PC | `.\scripts\run_local.ps1` |
| Abrir na outra internet (túnel) | `.\scripts\tunnel.ps1` |
| API + túnel juntos | `.\scripts\start.ps1` |

---

## 1. Primeira vez

```powershell
.\scripts\setup.ps1
copy .env.example .env
```

Edite `.env` e descomente `API_KEY=...` **antes** de expor o túnel.

---

## 2. Só neste PC

```powershell
.\scripts\run_local.ps1
```

- Docs: http://127.0.0.1:8000/docs  
- Health: http://127.0.0.1:8000/health  

```powershell
curl.exe http://127.0.0.1:8000/health
curl.exe -F "image=@foto.jpg" http://127.0.0.1:8000/v1/scan
curl.exe -F "images=@a.jpg" -F "images=@b.jpg" http://127.0.0.1:8000/v1/scan
```

---

## 3. Outro PC / celular em **outra internet**

O Wi-Fi da faculdade não alcança `127.0.0.1` da sua casa. O túnel cria um HTTPS público que aponta para a API local.

1. PC de casa **ligado**, sem sleep, API no ar (`run_local.ps1`).
2. Outro terminal:

```powershell
.\scripts\tunnel.ps1
```

3. O `cloudflared` imprime algo como `https://random-words.trycloudflare.com`.
4. No outro PC (4G, faculdade, qualquer rede):

```
https://ESSE-URL/docs
https://ESSE-URL/health
https://ESSE-URL/v1/scan
```

No app, a base URL é esse `https://...trycloudflare.com` (sem barra no final). Header `X-API-Key` se você definiu `API_KEY` no `.env`.

**URL do modo rápido muda toda vez** que você fecha o túnel. Para um endereço fixo: conta grátis Cloudflare → Zero Trust → Tunnels → hostname `ptcg-api.seudominio.com` → origem `http://localhost:8000`. Aí o app sempre usa o mesmo HTTPS.

Instalar o cliente (uma vez):

```powershell
winget install Cloudflare.cloudflared
```

Não abra porta no roteador. Teste no **4G**, não no Wi-Fi de casa.

---

## 4. API + túnel num comando

```powershell
.\scripts\start.ps1
```

Abre a API numa janela e o túnel nesta. Deixe as duas abertas.
