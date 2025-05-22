#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Script pour placer directement un ordre réel sans passer par le système complet
# Exécuter avec: python place_real_order.py

import os
import sys
import yaml
import random
import time
import math
from datetime import datetime

# Import IB sync classes directement


# PARAMÈTRES DE L'ORDRE (MODIFIEZ SELON BESOIN)
SYMBOL = "AAPL"        # Symbole de l'action
SIDE = "BUY"           # Direction (BUY ou SELL)
SL_PCT = 1.0           # Stop Loss en pourcentage (1.0 = 1%)
TP_PCT = 2.0           # Take Profit en pourcentage (2.0 = 2%)
SIZE = 1               # Nombre d'actions à acheter/vendre
HOST = '127.0.0.1'     # Adresse du serveur TWS/IB Gateway
PORT = 7497            # Port (7496 pour TWS live, 7497 pour TWS paper)
CLIENT_ID = random.randint(1000, 9999)  # ID client aléatoire

print(f"\n{'='*50}")

print(f"{'='*50}")

# Création d'une instance IB directe (sans passer par IBKRConnector)
ib = IB()

try:
    # Connexion à TWS/IB Gateway
    print("[INFO] Tentative de connexion directe à IBKR...")
    ib.connect(HOST, PORT, clientId=CLIENT_ID)
    
    if not ib.isConnected():
        print("[ERREUR] Impossible de se connecter à IBKR. Vérifiez que TWS est démarré et que les API sont activées.")
        sys.exit(1)
        
    print("[SUCCÈS] Connecté à IBKR!")
    
    # Récupération des informations du compte
    accounts = ib.managedAccounts()
    print(f"[INFO] Comptes disponibles: {accounts}")
    
    if not accounts:
        print("[ERREUR] Aucun compte disponible.")
        sys.exit(1)
    
    # Utilisation du premier compte disponible
    account = accounts[0]
    print(f"[INFO] Utilisation du compte: {account}")
    
    # Création du contrat pour l'action
    print(f"[INFO] Création du contrat pour {SYMBOL}...")
    contract = Stock(SYMBOL, 'SMART', 'USD')
    
    # Récupération du prix réel du marché
    print(f"[INFO] Récupération du prix réel pour {SYMBOL}...")
    
    # Créer un ticker pour obtenir les données de marché
    ticker = ib.reqMktData(contract, '', False, False)
    
    # Attendre que les données arrivent
    for i in range(5):
        ib.sleep(1)
        print(f"[INFO] Attente des données de marché... {i+1}s")
        if ticker.last or ticker.close or ticker.bid or ticker.ask:
            break
    
    # Afficher toutes les informations disponibles sur le ticker
    print(f"[DEBUG] Toutes les données de marché disponibles :")
    print(f"  Last: {ticker.last}")
    print(f"  Close: {ticker.close}")
    print(f"  Bid: {ticker.bid}")
    print(f"  Ask: {ticker.ask}")
    print(f"  High: {ticker.high}")
    print(f"  Low: {ticker.low}")
    
    # Déterminer le meilleur prix disponible avec vérification explicite des valeurs nan
    market_price = None
    if ticker.last and not math.isnan(ticker.last):
        market_price = ticker.last
        print(f"[INFO] Prix du dernier trade: {market_price}")
    elif ticker.close and not math.isnan(ticker.close):
        market_price = ticker.close
        print(f"[INFO] Prix de clôture: {market_price}")
    elif ticker.bid and ticker.ask and not math.isnan(ticker.bid) and not math.isnan(ticker.ask):
        market_price = (ticker.bid + ticker.ask) / 2
        print(f"[INFO] Prix moyen bid-ask: {market_price} (Bid: {ticker.bid}, Ask: {ticker.ask})")
    else:
        print(f"[ERREUR CRITIQUE] Aucun prix réel disponible. Impossible de placer un ordre sans données de marché fiables.")
        print(f"[INFO] Pour les données de marché en temps réel, vous devez soit :")
        print(f"  1. Souscrire aux données de marché en temps réel auprès d'IBKR")
        print(f"  2. Intégrer une autre source de données comme Yahoo Finance ou Alpha Vantage")
        print(f"[INFO] Déconnexion d'IBKR...")
        ib.disconnect()
        print(f"[INFO] Déconnecté.")
        sys.exit(1)  # Arrêt du programme avec code d'erreur
    
    # Calculer les prix SL et TP basés sur le prix réel et le pourcentage
    if SIDE.upper() == "BUY":
        action = "BUY"
        sl_price = round(market_price * (1 - SL_PCT/100), 2)  # SL est x% en dessous du prix d'entrée
        tp_price = round(market_price * (1 + TP_PCT/100), 2)  # TP est x% au-dessus du prix d'entrée
    else:  # SELL
        action = "SELL"
        sl_price = round(market_price * (1 + SL_PCT/100), 2)  # SL est x% au-dessus du prix d'entrée
        tp_price = round(market_price * (1 - TP_PCT/100), 2)  # TP est x% en dessous du prix d'entrée
        
    # Annuler la demande de données de marché après utilisation
    ib.cancelMktData(contract)
    
    print(f"[INFO] Détails de l'ordre:")
    print(f"  Symbole: {SYMBOL}")
    print(f"  Direction: {action}")
    print(f"  Stop Loss: {sl_price}")
    print(f"  Take Profit: {tp_price}")
    print(f"  Taille: {SIZE} unités")
    
    # Création de l'ordre principal
    print("[INFO] Création de l'ordre principal...")
    main_order = MarketOrder(action, SIZE)
    main_order.account = account  # Spécification du compte
    
    # Envoi de l'ordre
    print("[INFO] Envoi de l'ordre à IBKR...")
    trade = ib.placeOrder(contract, main_order)
    
    # Attente de confirmation - plus longue attente
    print("[INFO] Attente de confirmation de l'ordre...")
    for i in range(15):  # Attendre 15 secondes max
        ib.sleep(1)
        print(f"[INFO] Attente {i+1}s... Statut actuel: {trade.orderStatus.status}")
        if trade.orderStatus.status in ['Submitted', 'Filled', 'PreSubmitted']:
            print(f"[INFO] Ordre accepté avec statut: {trade.orderStatus.status}!")
            break
    
    print(f"[INFO] Statut final de l'ordre: {trade.orderStatus.status}")
    
    # Considérer PendingSubmit comme valide également
    if trade.orderStatus.status in ['Submitted', 'Filled', 'PreSubmitted', 'PendingSubmit']:
        print("[SUCCÈS] Ordre principal placé avec succès!")
        
        # Création d'un ordre SL
        print("[INFO] Création de l'ordre Stop Loss...")
        sl_order = StopOrder(
            'SELL' if action == 'BUY' else 'BUY',
            SIZE,
            sl_price
        )
        sl_order.account = account
        sl_order.parentId = trade.order.orderId  # Liaison avec l'ordre principal
        
        # Envoi de l'ordre SL
        sl_trade = ib.placeOrder(contract, sl_order)
        print(f"[INFO] Stop Loss placé: {sl_trade.order.orderId}")
        
        # Création d'un ordre TP
        print("[INFO] Création de l'ordre Take Profit...")
        tp_order = LimitOrder(
            'SELL' if action == 'BUY' else 'BUY',
            SIZE,
            tp_price
        )
        tp_order.account = account
        tp_order.parentId = trade.order.orderId  # Liaison avec l'ordre principal
        
        # Envoi de l'ordre TP
        tp_trade = ib.placeOrder(contract, tp_order)
        print(f"[INFO] Take Profit placé: {tp_trade.order.orderId}")
        
        print("\n[SUCCÈS] Ordre complet (principal + SL/TP) placé avec succès!")
    else:
        print(f"[ERREUR] L'ordre n'a pas été soumis correctement. Statut: {trade.orderStatus.status}")
    
except Exception as e:
    print(f"\n[ERREUR CRITIQUE] {e}")
    import traceback
    print(traceback.format_exc())
finally:
    # Déconnexion propre
    if ib.isConnected():
        print("[INFO] Déconnexion d'IBKR...")
        ib.disconnect()
        print("[INFO] Déconnecté.")
    else:
        print("[INFO] Déjà déconnecté.")

