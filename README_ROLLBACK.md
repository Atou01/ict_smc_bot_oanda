# Procédure de Rollback - Bot Forex

Ce document décrit la procédure pour revenir rapidement à la version stable du bot en cas de problème avec les modifications LLM.

## Procédure de Rollback (< 5 minutes)

1. **Arrêter le bot en cours d'exécution**
   ```powershell
   # Trouver et arrêter tous les processus python liés au bot
   Get-Process -Name python | Where-Object { $_.CommandLine -match "main.py" } | Stop-Process -Force
   ```

2. **Revenir à la branche de sauvegarde**
   ```powershell
   cd c:\Users\Administrator\Desktop\bot-vantage
   git checkout backup_preLLM_refactor
   ```

3. **Vérifier que vous êtes bien sur la branche de sauvegarde**
   ```powershell
   git branch
   # Vous devriez voir un astérisque (*) à côté de "backup_preLLM_refactor"
   ```

4. **Relancer le bot**
   ```powershell
   cd c:\Users\Administrator\Desktop\bot-vantage\src\bot
   python main.py
   ```

## Vérification post-rollback

Après avoir effectué le rollback, vérifiez que :

1. Les logs du bot démarrent normalement
2. Le terminal MT5 est correctement connecté
3. Les notifications Discord fonctionnent

Si tout est correct, le bot devrait fonctionner comme avant les modifications LLM, sans le nouveau module `llm_engine.py`.

## Notes importantes

- La branche `backup_preLLM_refactor` contient l'état exact du code qui fonctionnait en production avant les modifications LLM.
- Ne modifiez pas cette branche - elle sert uniquement de sauvegarde.
- Pour reprendre le développement après un rollback, créez une nouvelle branche à partir de `backup_preLLM_refactor`.
