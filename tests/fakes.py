OWNER = 1
STRANGER = 2
CHAT = 2_000_000_001


class FakeVk:
    def __init__(self, users=None, history=None):
        self.me_id = OWNER
        self.known = {OWNER: user(OWNER), STRANGER: user(STRANGER), **(users or {})}
        self._history = history or []
        self.sent, self.edited, self.deleted, self.uploads = [], [], [], []
        self.own_random_ids = set()

    def send(self, peer_id, text=None, **params):
        self.sent.append({"peer_id": peer_id, "text": text, **{k: v for k, v in params.items() if v is not None}})
        self.own_random_ids.add(10_000 + len(self.sent))
        return len(self.sent)

    def sent_by_bot(self, random_id):
        return bool(random_id) and random_id in self.own_random_ids

    def edit(self, peer_id, message_id, text):
        self.edited.append((peer_id, message_id, text))

    def delete(self, message_ids, for_all):
        self.deleted.append((list(message_ids), for_all))

    def history(self, peer_id, start_message_id, count=200):
        return self._history

    def user(self, user_id):
        found = self.users_by_ids([user_id])
        return found[0] if found else None

    def users(self, user_ids):
        return self.users_by_ids(user_ids)

    def users_by_ids(self, user_ids):
        keys = [int(u) if str(u).isdigit() else u for u in user_ids]
        return [self.known[k] for k in keys if k in self.known]

    def upload_voice(self, path, peer_id):
        self.uploads.append(("voice", path))
        return "audio_message1_10"


def user(user_id):
    return {"id": user_id, "first_name": f"Имя{user_id}", "last_name": "Фамилия"}


def message(text, from_id=OWNER, peer_id=CHAT, message_id=100, **extra):
    return {"id": message_id, "text": text, "from_id": from_id, "peer_id": peer_id, "attachments": [], **extra}


def texts(vk):
    return [m["text"] for m in vk.sent] + [e[2] for e in vk.edited]


def in_peer(vk, peer_id):
    return [m for m in vk.sent if m["peer_id"] == peer_id]
