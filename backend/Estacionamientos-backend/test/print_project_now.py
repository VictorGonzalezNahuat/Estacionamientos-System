from datetime import datetime, timezone

from core.datetime_utils import get_app_timezone_name, now_local_naive


def main() -> None:
    tz_name = get_app_timezone_name()
    now_project = now_local_naive()
    now_utc = datetime.now(timezone.utc)

    print("=== Proyecto: fecha/hora actual ===")
    print(f"APP_TIMEZONE: {tz_name}")
    print(f"now_local_naive (proyecto): {now_project}")
    print(f"now_local_naive isoformat: {now_project.isoformat(sep=' ', timespec='seconds')}")
    print(f"UTC actual (referencia): {now_utc.isoformat(timespec='seconds')}")


if __name__ == "__main__":
    main()
