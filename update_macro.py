#!/usr/bin/env python3
# Script pour mettre à jour les données macroéconomiques dans shared_state.json

from src.bot.macro_collector import MacroCollector
import json
import os

def main():
    print("Récupération des événements macroéconomiques...")
    collector = MacroCollector()
    collector.fetch_events()
    print("Récupération des événements terminée")
    
    # Générer le contexte macro
    macro_context = collector.get_macro_context()
    
    # Mettre à jour shared_state.json
    shared_state_path = os.path.join('logs', 'shared_state.json')
    try:
        with open(shared_state_path, 'r') as f:
            state = json.load(f)
        
        state['macro_context'] = macro_context
        
        with open(shared_state_path, 'w') as f:
            json.dump(state, f, indent=2)
        
        print(f"Données macroéconomiques mises à jour dans {shared_state_path}")
        print("Contenu du contexte macro:")
        print("-----------------------------------------------------")
        print(macro_context[:500] + "..." if len(macro_context) > 500 else macro_context)
        print("-----------------------------------------------------")
    except Exception as e:
        print(f"Erreur lors de la mise à jour de shared_state.json: {e}")

if __name__ == "__main__":
    main()
