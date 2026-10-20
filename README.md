# PTCG Scanner API

HTTP API de inferência do [PTCG Scanner](https://github.com/SofiaValadares/PTCG-Scanner) (TCC de **Sofia Valadares**). Recebe **uma ou várias fotos**, detecta as cartas (YOLO OBB), recorta em 63×88 mm, lê nome / número / coleção (RapidOCR) e devolve o match no catálogo.

Este repositório **não treina**. Os pesos de produção são `models/obb-v6.pt` e `models/ocr-roi-v3.pt`.

Licença: [CC BY-NC 4.0](LICENSE) — uso acadêmico com crédito; uso comercial reservado à autora (`sofiav.cav@gmail.com`). Marcas Pokémon: [NOTICE](NOTICE).

---

## Layout

```
API-PTCG Scanner/
├── app/                 FastAPI (rotas)
├── ptcg_api/            engine, catálogo, ROI 0°/180°
├── src/cropper/         recorte 63×88 mm
├── src/ocr/             RapidOCR nas faixas
├── models/              obb-v6.pt · ocr-roi-v3.pt
├── data/catalog/        CSVs por idioma
├── Dockerfile           deploy futuro (CPU)
└── docker-compose.yml
```

---

## Rodar (scripts)

Lista completa: [`COMANDOS.md`](COMANDOS.md).

```powershell
.\scripts\setup.ps1      # primeira vez (venv + pip)
.\scripts\run_local.ps1  # API neste PC → http://127.0.0.1:8000/docs
.\scripts\tunnel.ps1     # HTTPS para outro PC / outra internet
.\scripts\start.ps1      # API + túnel juntos
```

Se o PowerShell recusar o script: `powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1`.

`GET /health` confirma GPU/CPU e os pesos. Copie `.env.example` para `.env` e defina `API_KEY` **antes** de abrir o túnel.

---

## Chamada: uma ou várias imagens

Campo `images` repetido (várias) **ou** `image` (uma). JPEG, PNG, WebP, BMP. Até 20 arquivos / 12 MB cada (configurável).

**Uma foto**

```powershell
curl.exe -F "image=@foto.jpg" http://127.0.0.1:8000/v1/scan
```

**Várias fotos na mesma request**

```powershell
curl.exe -F "images=@binder1.jpg" -F "images=@binder2.jpg" http://127.0.0.1:8000/v1/scan
```

**Crops em JPEG Base64** (para o app mostrar a carta recortada)

```powershell
curl.exe -F "images=@foto.jpg" "http://127.0.0.1:8000/v1/scan?include_crops=true"
```

Resposta (resumo):

```json
{
  "image_count": 2,
  "card_count": 11,
  "elapsed_ms": 1840.2,
  "device": "0",
  "images": [
    {
      "filename": "binder1.jpg",
      "card_count": 9,
      "cards": [
        {
          "index": 0,
          "det_conf": 0.97,
          "orient_deg": 0,
          "ocr": { "name": "Pikachu", "number": "025/165", "collection": "MEW" },
          "match": {
            "name": "Pikachu",
            "number": "25/165",
            "set_id": "MEW",
            "set_name": "151",
            "score": 1115.0
          }
        }
      ]
    }
  ]
}
```

Se um arquivo da lista falhar, os outros ainda voltam; o item traz `"error"`.

---

## App (Flutter / React / etc.)

`multipart/form-data`, campo `images` (array de arquivos) ou `image`. Header opcional `X-API-Key` se `API_KEY` estiver no `.env`.

CORS default `*` (local). No deploy, defina `CORS_ORIGINS` com o domínio do app.

---

## Outra internet (túnel)

Passo a passo: [`COMANDOS.md`](COMANDOS.md) §3.

```powershell
winget install Cloudflare.cloudflared   # uma vez
.\scripts\start.ps1                     # API + túnel
```

O `cloudflared` mostra `https://….trycloudflare.com`. Esse URL vale de **qualquer** rede (4G, faculdade). O PC de casa precisa ficar ligado, sem sleep. O endereço temporário muda ao fechar o túnel; URL fixo = túnel nomeado na conta Cloudflare (detalhe no `COMANDOS.md`).

Defina `API_KEY` no `.env` e o mesmo valor no app (`X-API-Key`). Não abra porta no roteador. Teste no 4G, não no Wi-Fi de casa.

---

## Deploy futuro

| Destino | Como |
|---|---|
| Este PC + túnel | `uvicorn` + cloudflared (agora) |
| Docker (CPU) | `docker compose up --build` |
| Hugging Face Space | o `Dockerfile` desta pasta |
| Oracle Cloud / VM | o mesmo Docker, `DEVICE=cpu` |

GPU no Docker exige imagem NVIDIA; no TCC o caminho simples é o PC local.

---

## Pesos

| Arquivo | Papel |
|---|---|
| `models/obb-v6.pt` | Detector de carta (YOLOv26s-OBB, imgsz 960) |
| `models/ocr-roi-v3.pt` | Faixas name / number / colection (imgsz 800) |

OCR não tem `.pt` nosso: RapidOCR (ONNX no pacote). Atualizar pesos: copie de novo do repo do TCC (`models/`).

---

Valadares, Sofia. PTCG Scanner. 2026. CC BY-NC 4.0.
