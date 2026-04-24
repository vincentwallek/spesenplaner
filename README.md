# Reise-Spesen-Planer

Eine Full-Stack Microservice-Webanwendung zur Verwaltung des gesamten Lebenszyklus von Spesenanträgen — von der Einreichung bis zur Auszahlung.

## Architektur

```
┌──────────────┐     ┌──────────────┐
│   Angular    │────▶│  API Gateway │
│   Frontend   │     │  (Port 8000) │
│  (Port 4200) │     │   OAuth2/JWT │
└──────────────┘     └──────┬───────┘
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
          ▼                 ▼                 ▼
   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
   │  request-   │  │  budget-    │  │  payout-    │
   │  service    │  │  service    │  │  service    │
   │ (Port 3001) │  │ (Port 3003) │  │ (Port 3004) │
   └──────┬──────┘  └──────▲──────┘  └──────▲──────┘
          │ gRPC           │ REST           │ Kafka
          ▼                │                │
   ┌─────────────┐        │                │
   │  approval-  │────────┘      ┌─────────┘
   │  service    │               │
   │(3002/50051) │   ┌───────────┴───┐
   └─────────────┘   │    Kafka      │
                     │  (Port 9092)  │
                     └───────────────┘
```

### Kommunikationsprotokolle

| Route | Protokoll | Begründung |
|---|---|---|
| Frontend → API Gateway | REST | Browser-Standard |
| request → approval | **gRPC** | Performantes binäres Protokoll |
| approval → budget | **REST** | Direkte HTTP-Kette |
| budget → payout | **Kafka** | Asynchrone Event-Entkopplung |

### Microservice-Prinzipien

- ✅ **Zustandslos** — Kein Session-State in Services
- ✅ **Eigene Datenbank** — Jeder Service hat isolierte SQLite-DB
- ✅ **Eigene Businesslogik** — Klar abgegrenzte Domänen
- ✅ **HATEOAS** — Alle API-Responses enthalten Hypermedia-Links
- ✅ **OAuth2/JWT** — Zentralisierte Authentifizierung am API Gateway
- ✅ **Swagger/OpenAPI** — Automatische Doku unter `/docs`

## Technologie-Stack

| Komponente | Technologie |
|---|---|
| Frontend | Angular 18 (Standalone), TypeScript |
| Backend | Python 3.12, FastAPI, Uvicorn |
| Datenbank | SQLite (pro Service isoliert) |
| Auth | OAuth2 Password Grant, JWT (python-jose) |
| gRPC | grpcio, protobuf |
| Kafka | Confluent Kafka, aiokafka |
| Container | Docker, docker-compose |
| Orchestrierung | Kubernetes, HPA Autoscaling |
| API-Doku | Swagger UI (FastAPI automatisch) |

## Schnellstart (Lokal)

### Voraussetzungen
- Python 3.12+
- Node.js 20+
- Docker & Docker Compose

### Option 1: Docker Compose (empfohlen)

```bash
docker-compose up --build
```

Öffne: `http://localhost:8080` (Frontend) / `http://localhost:8000/docs` (API Gateway Swagger)

### Option 2: Manuell

**Terminal 1 — API Gateway:**
```bash
cd api-gateway
python -m venv venv
.\venv\Scripts\Activate.ps1   # Windows
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Terminal 2 — Request Service:**
```bash
cd backend/request-service
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
# gRPC Stubs generieren:
python -m grpc_tools.protoc -I../../proto --python_out=. --grpc_python_out=. ../../proto/approval.proto
uvicorn main:app --reload --port 3001
```

**Terminal 3 — Approval Service:**
```bash
cd backend/approval-service
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m grpc_tools.protoc -I../../proto --python_out=. --grpc_python_out=. ../../proto/approval.proto
uvicorn main:app --reload --port 3002
```

**Terminal 4 — Budget Service:**
```bash
cd backend/budget-service
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 3003
```

**Terminal 5 — Payout Service:**
```bash
cd backend/payout-service
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 3004
```

**Terminal 6 — Frontend:**
```bash
cd frontend
npm install
ng serve --open
```

### Demo-Zugangsdaten

| Benutzer | Passwort | Rolle |
|---|---|---|
| `demo` | `demo123` | user |
| `manager` | `manager123` | manager |
| `admin` | `admin123` | admin |

## Kubernetes Deployment

```bash
# Namespace erstellen
kubectl apply -f k8s/namespace.yaml

# Infrastruktur (Kafka)
kubectl apply -f k8s/kafka/

# Services deployen
kubectl apply -f k8s/api-gateway/
kubectl apply -f k8s/request-service/
kubectl apply -f k8s/approval-service/
kubectl apply -f k8s/budget-service/
kubectl apply -f k8s/payout-service/
kubectl apply -f k8s/frontend/

# Ingress
kubectl apply -f k8s/ingress.yaml
```

### HPA Autoscaling Begründung

| Service | min | max | CPU% | Begründung |
|---|---|---|---|---|
| api-gateway | 2 | 5 | 70% | Hochverfügbar, alle Requests passieren hier |
| request-service | 2 | 8 | 60% | Höchste Last (CRUD), frühes Scaling |
| approval-service | 1 | 4 | 70% | Mittlere Last, gRPC effizient |
| budget-service | 1 | 4 | 70% | Mittlere Last |
| payout-service | 1 | 3 | 75% | Kafka-Consumer, asynchron |
| frontend | 1 | 3 | 80% | Nginx, statische Dateien |

## API-Dokumentation

Jeder Service bietet automatische Swagger-UI:

| Service | Swagger URL |
|---|---|
| API Gateway | http://localhost:8000/docs |
| Request Service | http://localhost:3001/docs |
| Approval Service | http://localhost:3002/docs |
| Budget Service | http://localhost:3003/docs |
| Payout Service | http://localhost:3004/docs |

## Projektstruktur

```
reise-spesen-planer/
├── api-gateway/              # OAuth2, JWT, Reverse-Proxy
├── backend/
│   ├── request-service/      # CRUD + gRPC Client
│   ├── approval-service/     # gRPC Server + REST Client
│   ├── budget-service/       # REST + Kafka Producer
│   └── payout-service/       # Kafka Consumer + REST
├── frontend/                 # Angular 18 SPA
├── proto/                    # Shared gRPC Proto
├── k8s/                      # Kubernetes Manifests
├── docker-compose.yml
├── .gitignore
└── README.md
```
