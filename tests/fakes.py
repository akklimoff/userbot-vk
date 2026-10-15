OWNER = 1
STRANGER = 2
CHAT = 2_000_000_001


class FakeVk:
    def __init__(self, users=None, history=None, privacy=None):
        self.me_id = OWNER
        self.known = {OWNER: user(OWNER), STRANGER: user(STRANGER), **(users or {})}
        self._history = history or []
        self.privacy = privacy or {}
        self.privacy_values = {}
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

    def user(self, user_id, fields=None):
        found = self.users_by_ids([user_id])
        return found[0] if found else None

    def users(self, user_ids, fields=None):
        return self.users_by_ids(user_ids)

    def users_by_ids(self, user_ids):
        keys = [int(u) if str(u).isdigit() else u for u in user_ids]
        return [self.known[k] for k in keys if k in self.known]

    def privacy_value(self, key):
        return self.privacy_values.get(key) or {"owners": {"allowed": list(self.privacy.get(key, []))}}

    def set_privacy_allowed(self, key, owners):
        self.privacy[key] = list(owners)

    def upload_voice(self, path, peer_id):
        self.uploads.append(("voice", path))
        return "audio_message1_10"

    def upload_photo(self, path, peer_id):
        self.uploads.append(("photo", path))
        return "photo1_20"

    def upload_graffiti(self, path, peer_id):
        self.uploads.append(("graffiti", path))
        return "graffiti1_30"


def user(user_id, is_friend=1):
    return {"id": user_id, "first_name": f"Имя{user_id}", "last_name": "Фамилия", "is_friend": is_friend}


def message(text, from_id=OWNER, peer_id=CHAT, message_id=100, **extra):
    return {"id": message_id, "text": text, "from_id": from_id, "peer_id": peer_id, "attachments": [], **extra}


def texts(vk):
    return [m["text"] for m in vk.sent] + [e[2] for e in vk.edited]
