def main(event, context):
    return {
        "body": {
            "status": "ok",
            "mensaje": "ping funciona",
            "event": event
        }
    }