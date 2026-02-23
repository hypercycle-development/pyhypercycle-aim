import time
from pyhypercycle_aim import SimpleQueue, aim_uri, JSONResponseCORS

# Sync function outside class (safer for queuing)
def sync_echo(text):
    time.sleep(1)  # Simulate AI work
    return {"result": f"You said: {text}"}

class MyEchoAIM(SimpleQueue):
    manifest = {
        "name": "Echo AIM",
        "short_name": "echo",
        "version": "0.1",
        "documentation_url": "https://example.com/my-aim",
        "license": "Open",
        "terms_of_service": "",
        "author": "Jeffrey D Legacy Sr"
    }

    @aim_uri(uri="/echo", methods=["POST"],
             endpoint_manifest={
                 "input_body": {"text": "<Your message>"},
                 "output": "<JSON>",
                 "currency": "USD",
                 "price_per_call": {"estimated_cost": 0, "min": 0, "max": 0},
                 "documentation": "Echoes back your text",
                 "example_calls": [{"body": {"text": "hello"}, "output": {"result": "You said: hello"}}]
             })
    async def echo_call(self, request):
        data = await request.json()
        text = data.get("text", "nothing")
        result = await self.add_job(sync_echo, text)
        return JSONResponseCORS(result)

if __name__ == "__main__":
    aim = MyEchoAIM()
    aim.run(uvicorn_kwargs={"host": "0.0.0.0", "port": 8000})
