# ML Training Server (GPU) — Phase 3

This maps to the **ML Training Server (GPU)** node in the deployment diagram. It
is intentionally empty in Phase 1.

**Planned (Phase 3):**
- Reads training data from object storage (MinIO locally → GCS/S3 in cloud).
- Trains the three baseline models:
  - Deforestation detection — statistical change-point detection on NDVI time
    series (classical first; LSTM/CNN noted as a later swap).
  - Species distribution model — logistic regression / random forest over
    environmental covariates (scikit-learn).
  - Climate forecasting — ARIMA/SARIMA baseline.
- Publishes trained artifacts back to object storage; the **inference server**
  loads them. Training and inference stay decoupled per the deployment diagram.

Kept separate from `ml/inference/` so the GPU training image and the lightweight
inference image are built and scaled independently (NFR-3, NFR-7).
