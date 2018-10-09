import os
from mflog import getLogger
import json
from aiohttp import web, ClientSession, BasicAuth, ClientTimeout

import aiohttp_github_helpers as h

GITHUB_USER = os.environ['GITHUB_USER']
GITHUB_PASS = os.environ['GITHUB_PASS']
GITHUB_SECRET = os.environ['GITHUB_SECRET'].encode('utf8')
LOGGER = getLogger("github_webhook_no_pullrequest_on_master")
TIMEOUT = ClientTimeout(total=20)
AUTH = BasicAuth(GITHUB_USER, GITHUB_PASS)

GUIDE_URL = "https://help.github.com/articles/" \
    "changing-the-base-branch-of-a-pull-request/"

COMMENT1 = """
Hi ! I'm the MetworkBot.

Thank you for contributing to this project.

But we don't accept pull requests on `master` branch as said in our
contributing guide.

=> You have to change the base branch of your pull request to
`integration` branch.

It's very easy to do that by following this [github guide](%s).

Many thanks !
""" % GUIDE_URL

COMMENT2 = """
Hi ! I'm the MetworkBot.

Thank you for contributing a pull-request to the `integration` branch.

We will review it ASAP !
"""

STATUS_KWARGS = {
    "status_target_url": "https://github.com/metwork-framework/resources/"
    "blob/master/documents/CONTRIBUTING.md",
    "status_context": "no pullrequest on master",
    "status_description": "no pullrequest on master test"
}


async def handle(request):
    event = request['github_event']
    if event != 'pull_request':
        LOGGER.info("ignoring %s event" % event)
        return web.Response(text="ignoring %s event" % event)
    body = await request.read()
    decoded_body = json.loads(body.decode('utf8'))
    action = decoded_body['action']
    if action not in ('opened', 'edited'):
        LOGGER.info("ignoring action: %s" % action)
        return web.Response(text="Done")
    pr = decoded_body['pull_request']
    repo = decoded_body['repository']['name']
    owner = decoded_body['repository']['owner']['login']
    issue_number = pr['number']
    head_sha = pr['head']['sha']
    base_ref = pr['base']['ref']
    comment = None
    status_state = None
    if base_ref == 'master':
        status_state = "failure"
        comment = COMMENT1
    elif base_ref == "integration":
        status_state = "success"
        comment = COMMENT2
    if comment and status_state:
        async with ClientSession(auth=AUTH, timeout=TIMEOUT) as session:
            await h.github_create_status(session, owner, repo, head_sha,
                                         status_state, **STATUS_KWARGS)
            await h.github_post_comment(session, owner, repo, issue_number,
                                        comment)
    return web.Response(text="Done")

check_signature_middleware = \
    h.github_check_signature_middleware_factory(GITHUB_SECRET)
app = web.Application(middlewares=[check_signature_middleware,
                                   h.github_check_github_event])
app.router.add_get('/{tail:.*}', handle)
app.router.add_post('/{tail:.*}', handle)
