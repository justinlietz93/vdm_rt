from deterministic_vdm_bot import DeterministicConversationBot


def sample(family="attention", selector="restraint", aperture="attention", ops="DAMP RETREAT RELEASE"):
    return {
        "tick": 10,
        "true_top1_phrase": "I think I hold attention here.",
        "true_top1_family": family,
        "true_top1_leaf": "focusing",
        "selector_phrase": "I think I hold down the pressure.",
        "selector_family": selector,
        "selector_leaf": "suppression",
        "aperture_phrase": "I think I hold attention here.",
        "aperture_family": aperture,
        "aperture_leaf": "focusing",
        "true_topk_families": [family, selector, aperture],
        "active_ops": ops,
        "aperture_commands": "AP_NARROW",
        "channel": "pal_live",
    }


def test_deterministic_first_reply():
    a = DeterministicConversationBot(seed=123).step(sample()).to_dict()
    b = DeterministicConversationBot(seed=123).step(sample()).to_dict()
    assert a["reply_text"] == b["reply_text"]
    assert a["topic"] == b["topic"]


def test_no_terminal_action_code():
    bot = DeterministicConversationBot(seed=7)
    for i in range(20):
        pkt = bot.step(sample(family="restraint" if i % 2 else "attention"))
        assert "BOT ACTION" not in pkt.reply_text
        assert "Shift detected" not in pkt.reply_text
        assert "Hold restraint" not in pkt.reply_text
        assert 18 <= len(pkt.reply_text.split()) <= 75


def test_inertia_and_variation():
    bot = DeterministicConversationBot(seed=99)
    replies = []
    topics = []
    for i in range(12):
        pkt = bot.step(sample(family=["attention", "comparison", "uncertainty", "readiness"][i % 4]))
        replies.append(pkt.reply_text)
        topics.append(pkt.topic)
    assert len(set(replies)) >= 8
    # It can move, but should not thrash every turn.
    changes = sum(1 for a, b in zip(topics, topics[1:]) if a != b)
    assert changes <= 7


def test_questions_are_not_every_turn():
    bot = DeterministicConversationBot(seed=313)
    question_count = 0
    for i in range(18):
        fam = ["attention", "comparison", "readiness", "uncertainty"][i % 4]
        pkt = bot.step(sample(family=fam, selector="attention", aperture="attention", ops="RELEASE ADVANCE"))
        if pkt.reply_text.strip().endswith("?"):
            question_count += 1
    assert question_count <= 4
