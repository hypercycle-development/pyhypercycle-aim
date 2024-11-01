import asyncio
import inspect
import time

import uvicorn
from pyhypercycle_aim.util import to_async, JSONResponseCORS, default_exception_handlers, \
    aim_uri
from starlette.applications import Starlette
from starlette.routing import Route


class BaseServer:
    def get_user_address(self, request):
        return request.headers.get("hypc_user", None)

    def is_private_call(self, request):
        return request.headers.get("hypc_is_private", None)



class SimpleServer(BaseServer):
    """
        Helper server object that uses the aim_uri decorator.
    """
    def run(self, debug=True, exception_handlers=None,
                  on_startup=None, concurrent=1, sleep_time=0.25, 
                  starlette_kwargs=None, uvicorn_kwargs=None):
        if not starlette_kwargs:
            starlette_kwargs = {}
        if not uvicorn_kwargs:
            uvicorn_kwargs = {}
        if exception_handlers is None:
            exception_handlers = default_exception_handlers
        if on_startup is None:
            on_startup = []
        if hasattr(self, 'startup_job'):
            on_startup.append(self.startup_job)
        #collect routes from this server
        routes = []
        endpoints_manifest = []
        has_manifest_override = False
        for arg in dir(self):
            ff = getattr(self, arg)
            if callable(ff):
                if hasattr(ff, "_uri"):
                    if ff._uri == "/manifest.json":
                        has_manifest_override = True
                    routes.append(Route(ff._uri, ff, methods=ff._methods, **ff._kwargs))
                    endpoints_manifest.append(ff._endpoint_manifest)
        self.manifest_json = self.manifest.copy()
        self.manifest_json['endpoints'] = endpoints_manifest
        
        if has_manifest_override is False:
            routes.append(Route("/manifest.json", 
                                lambda *args, **kwargs: JSONResponseCORS(self.manifest_json),
                                methods=["GET"]))

        self.job_queue = []
        self.queue_counter = 0
        self.concurrent = concurrent
        self.sleep_time = sleep_time
        self.app = Starlette(debug=debug, routes=routes,
                             exception_handlers=exception_handlers,
                             on_startup = on_startup, **starlette_kwargs)
        uvicorn.run(self.app, **uvicorn_kwargs)


class SimpleQueue(BaseServer):
    """
        Helper server to serve an synchronous job process, like model inference.
    """
    def run(self, debug=True, exception_handlers=None,
                  on_startup=None, concurrent=1, sleep_time=0.25, 
                  starlette_kwargs=None, uvicorn_kwargs=None):
        if not starlette_kwargs:
            starlette_kwargs = {}
        if not uvicorn_kwargs:
            uvicorn_kwargs = {}
        if exception_handlers is None:
            exception_handlers = default_exception_handlers
        if on_startup is None:
            on_startup = []
        if hasattr(self, "startup_job"):
            on_startup.append(self.startup_job)
        #collect routes from this server
        routes = []
        endpoints_manifest = []
        has_manifest_override = False
        for arg in dir(self):
            ff = getattr(self, arg)
            if callable(ff):
                if hasattr(ff, "_uri"):
                    if ff._uri == "/manifest.json":
                        has_manifest_override = True
                    routes.append(Route(ff._uri, ff, methods=ff._methods, **ff._kwargs))
                    if ff._uri == "/queue":
                        endpoints_manifest.insert(0,ff._endpoint_manifest)
                    else:
                        endpoints_manifest.append(ff._endpoint_manifest)
        self.manifest_json = self.manifest.copy()
        self.manifest_json['endpoints'] = endpoints_manifest
        
        if has_manifest_override is False:
            routes.append(Route("/manifest.json", 
                                lambda *args, **kwargs: JSONResponseCORS(self.manifest_json),
                                methods=["GET"]))

        self.job_queue = []
        self.queue_counter = 0
        self.concurrent = concurrent
        self.sleep_time = sleep_time
        self.app = Starlette(debug=debug, routes=routes,
                             exception_handlers=exception_handlers,
                             on_startup = on_startup, **starlette_kwargs)
        uvicorn.run(self.app, **uvicorn_kwargs)

    async def queue_loop(self):
        while True:
            if len(self.job_queue) > 0:
                this_job = self.job_queue[0]
                if inspect.iscoroutinefunction(this_job['func']):
                    res = await this_job['func'](*this_job['args'], **this_job['kwargs'])
                else:
                    res = await to_async(this_job['func'], *this_job['args'],
                                         **this_job['kwargs'])

                this_job['result'] = res
                self.job_queue.pop(0)
                self.queue_counter+=1
            await asyncio.sleep(self.sleep_time)

    async def add_job(self, func, *args, **kwargs):
        job = {"func": func, "args": args, "kwargs": kwargs}
        self.job_queue.append(job)
        while True:
            await asyncio.sleep(self.sleep_time)
            if 'result' in job:
                return job['result']

    @aim_uri(uri="/queue", methods=["GET"], endpoint_manifest={
        "input_query": "",
        "input_body": "",
        "documentation": "Returns the next job number to be worked on, and the current length of the job queue. When calling /parse, jobs will be returned on a first-come first-serve manner. To get an idea of how large the queue is, and what your position in the queue will be in the future, you can call /queue first to get the current length, current job number, and next job number, and then call /parse. The next job number you recieved will tell you roughly what your job number is and while you're waiting for the /parse call to return, you can call /queue again and see what the current job number being processed is.",
        "input_headers": "",
        "currency": "nullpay",
        "example_calls": [{
            "method": "GET",
            "query": "",
            "headers": "",
            "output": {
                "current_job_number": 0,
                "next_job_number": 0,
                "queue_length": 0
            }
        }]
    })
    def queue(self, request):
        if request.headers.get("cost_only"):
            return JSONResponseCORS({"min": 0, "max": 0, "estimated_cost": 0, "currency": ""})
        return JSONResponseCORS({"current_job_number": self.queue_counter,
                                 "next_job_number": self.queue_counter+len(self.job_queue),
                                 "queue_length": len(self.job_queue)},
                                headers={"cost_used": "0", "currency": ""})
        
    def startup_job(self):
        asyncio.create_task(self.queue_loop())


class AsyncQueue(BaseServer):
    """
        Helper server to serve an async job process, like training a model.
    """
    #############
    def run(self, debug=True, exception_handlers=None,
                  on_startup=None, concurrent=1, sleep_time=0.25, 
                  starlette_kwargs=None, uvicorn_kwargs=None):
        if not starlette_kwargs:
            starlette_kwargs = {}
        if not uvicorn_kwargs:
            uvicorn_kwargs = {}
        if exception_handlers is None:
            exception_handlers = default_exception_handlers
        if on_startup is None:
            on_startup = []

        on_startup.append(queue_startup)
        try:
            on_startup.append(self.startup_job)
        except:
            pass
        #collect routes from this server
        routes = []
        endpoints_manifest = []
        has_manifest_override = False
        for arg in dir(self):
            ff = getattr(self, arg)
            if callable(ff):
                if hasattr(ff, "_uri"):
                    if ff._uri == "/manifest.json":
                        has_manifest_override = True
                    routes.append(Route(ff._uri, ff, methods=ff._methods, **ff._kwargs))
                    if ff._uri == "/queue":
                        endpoints_manifest.insert(0,ff._endpoint_manifest)
                    else:
                        endpoints_manifest.append(ff._endpoint_manifest)
        self.manifest_json = self.manifest.copy()
        self.manifest_json['endpoints'] = endpoints_manifest
        if hasattr(self, "manifest_uri_order"):
            new_endpoints = []
            for entry in self.manifest_uri_order:
                for ep,k in enumerate(endpoints_manifest):
                    if ep['uri'] == entry:
                        break
                else:
                    continue
                new_endpoints.append(ep)
                del endpoints_manifest[k]
            new_endpoints.extend(endpoints_manifest)
            self.manifest_json['endpoints'] = new_endpoints
                    
        if has_manifest_override is False:
            routes.append(Route("/manifest.json", 
                                lambda *args, **kwargs: JSONResponseCORS(self.manifest_json),
                                methods=["GET"]))

        self.job_queue = []
        self.queue_counter = 0
        self.concurrent = concurrent
        self.sleep_time = sleep_time
        self.app = Starlette(debug=debug, routes=routes,
                             exception_handlers=exception_handlers,
                             on_startup = on_startup, **starlette_kwargs)
        uvicorn.run(self.app, **uvicorn_kwargs)

    #########################
    def queue_startup(self):
        asyncio.create_task(self.queue_loop())

    async def queue_loop(self):
        while True:
            if len(self.job_queue) > 0:
                this_job = self.job_queue[0]
                res = await to_async(this_job['func'], *this_job['args'], 
                                     **this_job['kwargs'])
                this_job['result'] = res
                this_job['finish_job'](res)
                print("finished job")
                self.job_queue.pop(0)
                self.queue_counter+=1
            await asyncio.sleep(self.sleep_time)

    #########################
    async def add_job(self, func, finish_job, *args, **kwargs):
        job_number = self.queue_counter
        job = {"func": func, "finish_job": finish_job, "args": args, "kwargs": kwargs, "job_number": job_number}
        self.job_queue.append(job)
        return job_number

    #########################
    @aim_uri(uri="/queue", methods=["GET"], endpoint_manifest={
        "input_query": "",
        "input_body": "",
        "documentation": "Returns the next job number to be worked on, and the current length of the job queue. When calling /parse, jobs will be returned on a first-come first-serve manner. To get an idea of how large the queue is, and what your position in the queue will be in the future, you can call /queue first to get the current length, current job number, and next job number, and then call /parse. The next job number you recieved will tell you roughly what your job number is and while you're waiting for the /parse call to return, you can call /queue again and see what the current job number being processed is.",
        "input_headers": "",
        "currency": "nullpay",
        "example_calls": [{
            "method": "GET",
            "query": "",
            "headers": "",
            "output": {
                "current_job_number": 0,
                "next_job_number": 0,
                "queue_length": 0
            }
        }]
    })
    def queue(self, request):
        if request.headers.get("cost_only"):
            return JSONResponseCORS({"min": 0, "max": 0, "estimated_cost": 0, "currency": ""})
        return JSONResponseCORS({"current_job_number": self.queue_counter,
                                 "next_job_number": self.queue_counter+len(self.job_queue),
                                 "queue_length": len(self.job_queue)},
                                headers={"cost_used": "0", "currency": ""})







class ExampleUsageSimple(SimpleQueue):
    manifest = {"name":"Example",
                "short_name": "example",
                "version": "0.1",
                "documentation_url": "...",
                "license": "Open",
                "terms_of_service": "",
                "author": "Barry Rowe"
               }

    @aim_uri(uri="/model", methods=["GET", "POST"],
             endpoint_manifest = {
                 "input_query": "",
                 "input_headers": {},
                 "input_body": {"text": "<Text>"},
                 "output": "<JSON>",
                 "currency": "USD",
                 "price_per_call": {"estimated_cost": 0, "min": 0, 
                                    "max": 0.1},
                 "price_per_mb": {"estimated_cost": 0, "min": 0, 
                                  "max": 0.1},
                 "documentation": "Take a call",
                 "example_calls": [{"body": {"text": "hi."},
                                    "method": "POST",
                                    "query": "",
                                    "headers": "",
                                    "output": {"output": "hello there."}}]
             })         
    async def model_call(self, request):
        def sync_function(sleep_time):
            #some synchronous call that takes a long time,
            #for example, model inference.
            time.sleep(sleep_time)
            return {"result": "done"}
        data = await self.add_job(sync_function, 4)
        return JSONResponseCORS(data)


def main():
    #example usage:
    app = ExampleUsageSimple()
    app.run(uvicorn_kwargs={"port": 4000, "host": "0.0.0.0"})

if __name__=='__main__':
    main()

