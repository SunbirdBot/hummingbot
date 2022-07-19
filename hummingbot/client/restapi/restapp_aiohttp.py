import asyncio
import aiohttp
from aiohttp import web


routes = web.RouteTableDef()


# @routes.get('/')
# async def hello(request):
#     return web.Response(text="Hello, world")


# @routes.get('/path/{name}')
# async def variable_handler(request):
#     return web.Response(
#         text="Hello, {}".format(request.match_info['name']))


class UIHandler:

    def __init__(self, command_handler, get_msg_from_queue):
        self._command_handler = command_handler
        self._get_msg_from_queue = get_msg_from_queue

    async def handle_status(self, request):
        msg = {'cmd': 'status'}
        await self._command_handler(msg)
        resp = await self._get_msg_from_queue()
        return web.Response(text="\n".join(resp))

    async def handle_greeting(self, request):
        name = request.match_info.get('name', "Anonymous")
        txt = "Hello, {}".format(name)
        return web.Response(text=txt)


async def main(command_handler, get_msg_from_queue):
    app = web.Application()

    handler = UIHandler(command_handler, get_msg_from_queue)
    app.add_routes([web.get('/status', handler.handle_status),
                    web.get('/greet/{name}', handler.handle_greeting)])

    # app.add_routes(routes)
    runner = aiohttp.web.AppRunner(app)
    await runner.setup()
    site = aiohttp.web.TCPSite(runner)
    # starts local webserver on port 8080
    # so you can access like http://localhost:8080/status
    await site.start()

    # add more stuff to the loop, if needed

    # wait forever
    await asyncio.Event().wait()

# asyncio.run(main())
