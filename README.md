# 🌐 IoT Data Lake Intelligent avec Classification ML

> Projet académique Master Big Data AI - Stockage des Données IoT: Avancées et Défis

## 📋 Description

Ce projet implémente un système de stockage intelligent pour les données IoT utilisant une classification par Machine Learning pour optimiser la répartition des données entre différents niveaux de stockage (Hot/Warm/Cold).

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    IoT Sensors (Simulated)                   │
│  🌡️ Temperature  💧 Humidity  ⚡ Energy  🚗 Motion           │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                 ML Classification Engine                     │
│                  🤖 Random Forest Classifier                 │
│         Critical │ Important │ Routine                       │
└─────────┬────────────┬────────────┬─────────────────────────┘
          │            │            │
          ▼            ▼            ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ 🔥 HOT      │ │ 🌤️ WARM     │ │ ❄️ COLD     │
│ In-Memory   │ │ SQLite      │ │ Compressed  │
│ < 1ms       │ │ < 10ms      │ │ Archives    │
└─────────────┘ └─────────────┘ └─────────────┘
```

## 🚀 Installation

```bash
# Cloner et naviguer vers le projet
cd IoT-DataLake-Project

# Installer les dépendances
pip install -r requirements.txt
```

## ▶️ Lancement

### Backend API
```bash
python -m uvicorn backend.main:app --reload --port 8000
```

### Dashboard Frontend
```bash
streamlit run frontend/dashboard.py
```

## 📊 Fonctionnalités

- ✅ Simulation de capteurs IoT temps réel
- ✅ Classification ML automatique des données
- ✅ Stockage multi-niveaux (Hot/Warm/Cold)
- ✅ Dashboard interactif avec métriques
- ✅ Détection d'anomalies
- ✅ Compression adaptative
