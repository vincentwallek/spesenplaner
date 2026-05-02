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
| Frontend → API Gateway | REST | Industriestandard für Web-Clients |
| request → approval | **gRPC** | Hochperformantes binäres Protokoll für interne Kommunikation |
| approval → budget | **REST** | Synchrone Kommunikation für Validierungsketten |
| budget → payout | **Kafka** | Asynchrone Event-Entkopplung für resiliente Auszahlungsprozesse |

### Microservice-Prinzipien

- **Zustandslosigkeit** — Die Services halten keinen Session-State.
- **Isolierte Datenhaltung** — Jeder Service verfügt über eine eigene, isolierte SQLite-Datenbank.
- **Domänentrennung** — Klare Abgrenzung der Businesslogik nach fachlichen Domänen.
- **HATEOAS** — API-Antworten enthalten Hypermedia-Links zur Navigation.
- **Zentrale Sicherheit** — OAuth2/JWT-basierte Authentifizierung und Autorisierung am API Gateway.
- **Standardisierte Dokumentation** — Automatische API-Dokumentation via Swagger/OpenAPI.

## Technologie-Stack

| Komponente | Technologie |
|---|---|
| Frontend | Angular 18 (Standalone), TypeScript |
| Backend | Python 3.12, FastAPI, Uvicorn |
| Datenbank | SQLite (pro Service isoliert) |
| Sicherheit | OAuth2 Password Grant, JWT (python-jose) |
| gRPC | grpcio, protobuf |
| Messaging | Confluent Kafka, aiokafka |
| Containerisierung | Docker, Docker Compose |
| Orchestrierung | Kubernetes, HPA Autoscaling |
| Dokumentation | Swagger UI (FastAPI Integration) |

## Schnellstart-Anleitung

### Voraussetzungen
- Python 3.12 oder höher
- Node.js 20 oder höher
- Docker & Docker Desktop (für Kubernetes)

### Option 1: Bereitstellung mittels Docker Compose (empfohlen)

Verwenden Sie den folgenden Befehl, um das gesamte System inklusive Infrastruktur zu starten:

```bash
docker-compose up --build
```

Die Anwendung ist anschließend unter den folgenden URLs erreichbar:
- Frontend: `http://localhost:8080`
- API Gateway Dokumentation: `http://localhost:8000/docs`

### Option 2: Manuelle Einrichtung für Entwicklungszwecke

**Terminal 1 — API Gateway:**
```bash
cd api-gateway
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Terminal 2 — Request Service:**
```bash
cd backend/request-service
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
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

### Authentifizierung

Für Testzwecke stehen folgende Konten zur Verfügung:

| Benutzer | Passwort | Rolle |
|---|---|---|
| `demo` | `demo123` | Benutzer |
| `manager` | `manager123` | Manager |
| `admin` | `admin123` | Administrator |

## Kubernetes Deployment (Docker Desktop)

Die folgende Anleitung ist speziell für den Betrieb unter **Docker Desktop** optimiert. Da Docker Desktop die lokalen Images direkt mit dem integrierten Kubernetes-Cluster teilt, ist kein manueller "Image Load" erforderlich.

### 1. Erstellung der Container-Images

Führen Sie diese Befehle im Hauptverzeichnis des Projekts aus, um alle erforderlichen Images zu bauen:

```powershell
docker build -t rsp/api-gateway:latest -f api-gateway/Dockerfile .
docker build -t rsp/request-service:latest -f backend/request-service/Dockerfile .
docker build -t rsp/approval-service:latest -f backend/approval-service/Dockerfile .
docker build -t rsp/budget-service:latest -f backend/budget-service/Dockerfile .
docker build -t rsp/payout-service:latest -f backend/payout-service/Dockerfile .
docker build -t rsp/frontend:latest -f frontend/Dockerfile .
```

### 2. Infrastruktur und Namespace vorbereiten

Erstellen Sie den Namespace und rollen Sie die grundlegende Infrastruktur aus:

```powershell
# Namespace initialisieren
kubectl create namespace reise-spesen-planer --dry-run=client -o yaml | kubectl apply -f -

# Zookeeper und Kafka bereitstellen
kubectl apply -f k8s/kafka/
```

### 3. Deployment der Microservices

Rollen Sie die Anwendungsdienste aus:

```powershell
kubectl apply -f k8s/api-gateway/
kubectl apply -f k8s/request-service/
kubectl apply -f k8s/approval-service/
kubectl apply -f k8s/budget-service/
kubectl apply -f k8s/payout-service/
kubectl apply -f k8s/frontend/
```

### 4. Zugriff konfigurieren (Port-Forwarding)

Um die Dienste lokal erreichbar zu machen, führen Sie folgende Befehle in jeweils separaten Terminal-Fenstern aus:

```powershell
# Frontend (Erreichbar unter http://localhost:8080)
kubectl port-forward svc/frontend 8080:80 -n reise-spesen-planer

# API Gateway (Erforderlich für die Kommunikation mit dem Backend)
kubectl port-forward svc/api-gateway 8000:8000 -n reise-spesen-planer
```

### 5. Bereinigung der Ressourcen

Zum Beenden der lokalen Umgebung und zum Entfernen der Ressourcen nutzen Sie folgende Befehle:

#### Port-Forwarding beenden
```powershell
Stop-Process -Name kubectl -Force -ErrorAction SilentlyContinue
```

#### Ressourcen entfernen (Optional)
```powershell
kubectl delete namespace reise-spesen-planer
```

## Analyse der HPA-Konfiguration

Das System nutzt Horizontal Pod Autoscaling (HPA) zur Lastverteilung. Aufgrund der Verwendung von SQLite-Datenbanken in der aktuellen Entwicklungsphase sind einige Dienste auf eine Instanz limitiert, um die Datenintegrität zu gewährleisten.

| Service | Min | Max | CPU Schwellenwert | Anmerkung |
|---|---|---|---|---|
| api-gateway | 1 | 1 | 70% | Zentrale Instanz zur Wahrung der Konsistenz |
| request-service | 1 | 1 | 60% | Limitierung durch Dateisperren in SQLite |
| approval-service | 1 | 1 | 70% | Konsistente gRPC-Verarbeitung |
| budget-service | 1 | 1 | 70% | Integrität der Finanzprüfungen |
| payout-service | 1 | 1 | 75% | Singleton-Consumer für Kafka-Events |
| frontend | 2 | 5 | 80% | Hochverfügbarer, zustandsloser Webserver für statische Assets |

## API-Endpunkte

Jeder Microservice verfügt über eine integrierte Swagger-Oberfläche:

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
├── api-gateway/              # Sicherheit und Routing
├── backend/
│   ├── request-service/      # Antragsverwaltung
│   ├── approval-service/     # Genehmigungsworkflow
│   ├── budget-service/       # Budgetprüfung
│   └── payout-service/       # Auszahlungsabwicklung
├── frontend/                 # Angular Client
├── proto/                    # Gemeinsame gRPC Definitionen
├── k8s/                      # Kubernetes Konfigurationen
├── docker-compose.yml        # Orchestrierung lokal
├── .gitignore
└── README.md
```
