from pathlib import Path

from app.core.config import Settings


def test_settings_resolve_secret_file_values(tmp_path: Path):
    secret_key_file = tmp_path / "secret_key.txt"
    mail_password_file = tmp_path / "mail_password.txt"
    mail_username_file = tmp_path / "mail_username.txt"
    mail_from_file = tmp_path / "mail_from.txt"

    secret_key_file.write_text("secret-from-file\n", encoding="utf-8")
    mail_password_file.write_text("mail-pass\n", encoding="utf-8")
    mail_username_file.write_text("mail-user@example.com\n", encoding="utf-8")
    mail_from_file.write_text("sender@example.com\n", encoding="utf-8")

    settings = Settings(
        _env_file=None,
        SECRET_KEY="",
        SECRET_KEY_FILE=str(secret_key_file),
        MAIL_PASSWORD="",
        MAIL_PASSWORD_FILE=str(mail_password_file),
        MAIL_USERNAME="",
        MAIL_USERNAME_FILE=str(mail_username_file),
        MAIL_FROM="",
        MAIL_FROM_FILE=str(mail_from_file),
    )

    assert settings.SECRET_KEY == "secret-from-file"
    assert settings.MAIL_PASSWORD == "mail-pass"
    assert settings.MAIL_USERNAME == "mail-user@example.com"
    assert settings.MAIL_FROM == "sender@example.com"


def test_settings_keep_inline_values_without_secret_files():
    settings = Settings(
        _env_file=None,
        SECRET_KEY="inline-secret",
        MAIL_PASSWORD="inline-password",
        MAIL_USERNAME="inline@example.com",
        MAIL_FROM="sender@example.com",
    )

    assert settings.SECRET_KEY == "inline-secret"
    assert settings.MAIL_PASSWORD == "inline-password"
    assert settings.MAIL_USERNAME == "inline@example.com"
    assert settings.MAIL_FROM == "sender@example.com"
