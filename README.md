# Bot Forex ICT/SMC avec IBKR

Projet Python pour un bot de trading Forex automatisé basé sur les Smart Money Concepts (ICT/SMC), connecté à l'API IBKR v20.

## Structure du projet

```
bot_vantage_mt5/
├─ config.yaml          # Configuration IBKR, symboles, timeframes, risk, calendar
├─ requirements.txt     # Dépendances Python
├─ README.md            # Ce fichier
├─ main.py              # Point d’entrée et scheduler
├─ data.py              # Client IBKR: fetch OHLC
├─ strategy.py          # Détection Order Blocks FVG BOS/CHoCH
├─ filter_news.py       # Filtrage des événements économiques
├─ risk.py              # Calcul de la taille de position (1% risk)
├─ broker.py            # Wrapper IBKR pour passer les ordres
├─ journal.py           # Journalisation des signaux et trades
└─ dashboard.py         # Interface Streamlit de suivi
```
