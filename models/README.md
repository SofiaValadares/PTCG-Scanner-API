# Models

Pesos de produção (os mesmos do repo do TCC):

| Arquivo | Papel |
|---|---|
| `obb-v6.pt` | Detector de carta |
| `ocr-roi-v3.pt` | Faixas de texto (ROI) |

Não há `.pt` de OCR. RapidOCR traz o ONNX no pip.

**Não commite os `.pt`.** A API procura primeiro em `models/` desta pasta; se não achar, usa os do TCC irmão (`../TCGTradeSegmentacao/models/`). Para ter uma cópia local: copie `obb-v6.pt` e `ocr-roi-v3.pt` do TCC.
