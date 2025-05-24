import requests
import yaml
import os


# Chargement sécurisé de la configuration
def load_discord_webhooks():
    config_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "../../config/config.yaml")
    )
    try:
        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f)
            discord_cfg = cfg.get("DISCORD", {})
            security = discord_cfg.get("security_webhook_url", "")
            notif = discord_cfg.get("notif_webhook_url", "")
            legacy = discord_cfg.get("webhook_url", "")
            return security, notif, legacy
    except Exception as e:
        print(f"[DISCORD] Erreur chargement config : {e}")
        return "", "", ""


def send_discord_notification(
    message, type="notif", username="TradePilotBot", silent_on_fail=True
):
    """
    Envoie une notification sur Discord selon le type :
    - type = 'security' => webhook sécurité
    - type = 'notif' => webhook notifications générales
    Si le webhook correspondant n'est pas défini, tente le legacy, sinon n'envoie rien.
    """
    # Appel direct à la fonction qui est déjà dans ce même fichier
    security, notif, legacy = load_discord_webhooks()
    url = ""
    if type == "security" and security:
        url = security
    elif type == "notif" and notif:
        url = notif
    elif legacy:
        url = legacy
    else:
        if not silent_on_fail:
            print(f"[DISCORD] Aucun webhook configuré pour type '{type}'")
        return False
    data = {"content": message, "username": username}
    try:
        resp = requests.post(url, json=data, timeout=7)
        if resp.status_code != 204:
            if not silent_on_fail:
                print(f"[DISCORD] Erreur envoi : {resp.status_code} {resp.text}")
            return False
        return True
    except Exception as e:
        if not silent_on_fail:
            print(f"[DISCORD] Exception lors de l'envoi : {e}")
        return False
