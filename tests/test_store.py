import json
import threading

from userbot.store import Store


def test_changes_survive_restart(tmp_path):
    path = str(tmp_path / "state" / "data.json")
    store = Store(path)
    assert store.add_to("banned", 5)
    assert not store.add_to("banned", 5)
    assert store.put_new("assoc", "а", "/uid")
    assert store.toggle("disabled")
    reopened = Store(path)
    assert reopened.get("banned") == [5]
    assert reopened.get("assoc") == {"а": "/uid"}
    assert reopened.get("disabled") is True


def test_reads_legacy_data_json(tmp_path):
    path = tmp_path / "data.json"
    path.write_text('{"ignore": [3], "saved_audio": {"k": "audio_message1_2_x"}}', encoding="utf-8")
    store = Store(str(path))
    assert store.get("ignore") == [3]
    assert store.remove_from("ignore", 3)
    assert not store.remove_from("ignore", 3)


def test_corrupt_file_is_kept_aside(tmp_path):
    path = tmp_path / "data.json"
    path.write_text("{oops", encoding="utf-8")
    store = Store(str(path))
    assert store.get("banned") is None
    assert (tmp_path / "data.json.broken").read_text(encoding="utf-8") == "{oops"


def test_get_returns_a_copy(tmp_path):
    store = Store(str(tmp_path / "data.json"))
    store.add_to("banned", 1)
    store.get("banned").append(2)
    assert store.get("banned") == [1]


def test_concurrent_writes_are_not_lost(tmp_path):
    path = tmp_path / "data.json"
    store = Store(str(path))
    threads = [threading.Thread(target=store.add_to, args=("banned", i)) for i in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(json.loads(path.read_text(encoding="utf-8"))["banned"]) == list(range(50))
    assert not (tmp_path / "data.json.tmp").exists()
