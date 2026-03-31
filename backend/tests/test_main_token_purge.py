from app import main


def test_record_token_purge_failure_escalates_after_threshold(monkeypatch):
    critical_mock = []

    def record(message, count):
        critical_mock.append((message, count))

    monkeypatch.setattr(main._logger, "critical", record)
    main._consecutive_token_purge_failures = 0

    for _ in range(main._TOKEN_PURGE_FAILURE_THRESHOLD):
        main._record_token_purge_failure()

    assert critical_mock == [
        ("Token purge has failed %d consecutive times", main._TOKEN_PURGE_FAILURE_THRESHOLD)
    ]


def test_record_token_purge_success_resets_counter():
    main._consecutive_token_purge_failures = 2

    main._record_token_purge_success()

    assert main._consecutive_token_purge_failures == 0
