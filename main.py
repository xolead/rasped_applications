import sys
from api_client import ForemClient, ForemAPIError
from storage_key import save_api_key, load_api_key, clear_api_key


def input_nonempty(prompt: str) -> str:
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("Поле не может быть пустым. Попробуйте снова.")


def ensure_authenticated(client: ForemClient) -> bool:
    if not client.api_key:
        print("\n🔐 Требуется API-ключ Forem.")
        print("Получить: dev.to → Settings → Account → DEV API Keys")
        key = input_nonempty("Вставьте api-key: ")
        client.api_key = key

    try:
        user = client.verify_key()
        print(f"✅ Аутентификация успешна: {user.get('username')} "
              f"({user.get('name')})")
        # Только после успешной проверки сохраняем ключ
        save_api_key(client.api_key)
        return True
    except ForemAPIError as e:
        print(f"❌ Ошибка аутентификации: {e}")
        client.api_key = None
        return False


def print_article(a: dict) -> None:
    print(f"  ID: {a.get('id')}")
    print(f"  Заголовок: {a.get('title')}")
    print(f"  URL: {a.get('url')}")
    print(f"  Published: {a.get('published')}")
    if a.get("published_at"):
        print(f"  Опубликовано: {a.get('published_at')}")


def do_create(client: ForemClient) -> None:
    print("\n--- CREATE: новая статья ---")
    if not ensure_authenticated(client):
        return  
    title = input_nonempty("Заголовок: ")
    body = input_nonempty("Текст (Markdown, в одну строку): ")
    tags = input("Теги (через запятую, опционально): ").strip()
    published_choice = input("Опубликовать сразу? (y/N): ").strip().lower()
    published = published_choice == "y"

    article = client.create_article(
        title=title, body_markdown=body,
        published=published, tags=tags,
    )
    print("\n✅ Статья создана:")
    print_article(article)


def do_read(client: ForemClient) -> None:
    print("\n--- READ: получить статью по ID ---")
    try:
        article_id = int(input_nonempty("ID статьи: "))
    except ValueError:
        print("❌ ID должен быть числом.")
        return
    article = client.get_article(article_id)
    print("\n📄 Статья:")
    print_article(article)


def do_update(client: ForemClient) -> None:
    print("\n--- UPDATE: обновить статью ---")
    if not ensure_authenticated(client):
        return
    try:
        article_id = int(input_nonempty("ID статьи для обновления: "))
    except ValueError:
        print("❌ ID должен быть числом.")
        return

    print("Оставьте поле пустым, чтобы не менять.")
    new_title = input("Новый заголовок: ").strip()
    new_body = input("Новый текст (Markdown): ").strip()
    new_published = input("Опубликовать? (y/n/пусто): ").strip().lower()

    fields = {}
    if new_title:
        fields["title"] = new_title
    if new_body:
        fields["body_markdown"] = new_body
    if new_published in ("y", "n"):
        fields["published"] = (new_published == "y")

    if not fields:
        print("ℹ️  Ничего не изменено.")
        return

    article = client.update_article(article_id, **fields)
    print("\n✅ Статья обновлена:")
    print_article(article)


def do_delete(client: ForemClient) -> None:
    print("\n--- DELETE: снять статью с публикации ---")
    if not ensure_authenticated(client):
        return
    try:
        article_id = int(input_nonempty("ID статьи: "))
    except ValueError:
        print("❌ ID должен быть числом.")
        return

    confirm = input(f"Снять статью {article_id} с публикации? (y/N): ")
    if confirm.strip().lower() != "y":
        print("Отменено.")
        return

    article = client.unpublish_article(article_id)
    print("\n🗑  Статья снята с публикации:")
    print_article(article)


def do_list_my(client: ForemClient) -> None:
    print("\n--- READ: мои статьи ---")
    if not ensure_authenticated(client):
        return
    articles = client.list_my_articles()
    if not articles:
        print("У вас пока нет статей.")
        return
    print(f"Всего: {len(articles)}")
    for a in articles:
        print_article(a)
        print("  ---")


def do_logout(client: ForemClient) -> None:
    clear_api_key()
    client.api_key = None
    print("🔓 Ключ удалён. Следующая операция потребует повторного входа.")


MENU = """
=====================================================
 Forem (DEV) CRUD-клиент
=====================================================
 1. CREATE — создать статью (нужна аутентификация)
 2. READ   — получить статью по ID
 3. READ   — список моих статей (нужна аутентификация)
 4. UPDATE — обновить статью (нужна аутентификация)
 5. DELETE — снять статью с публикации (нужна аутентификация)
 6. Показать статус аутентификации
 7. Выйти из аккаунта (удалить сохранённый ключ)
 0. Выход из программы
=====================================================
"""


def main() -> None:
    api_key = load_api_key()
    client = ForemClient(api_key=api_key)

    if api_key:
        print("🔐 Найден сохранённый API-ключ. Проверяем…")
        try:
            user = client.verify_key()
            print(f"✅ Авторизован как {user.get('username')} "
                  f"(повторная аутентификация не требуется).")
        except ForemAPIError as e:
            print(f"⚠️  Сохранённый ключ недействителен: {e}")
            client.api_key = None
    else:
        print("ℹ️  Сохранённого ключа нет. "
              "Он будет запрошен при первой авторизованной операции.")

    actions = {
        "1": do_create,
        "2": do_read,
        "3": do_list_my,
        "4": do_update,
        "5": do_delete,
        "6": lambda c: print(
            f"Текущий статус: "
            f"{'авторизован' if c.api_key else 'не авторизован'}"
        ),
        "7": do_logout,
    }

    while True:
        print(MENU)
        choice = input("Выберите пункт: ").strip()

        if choice == "0":
            print("👋 До встречи!")
            sys.exit(0)

        action = actions.get(choice)
        if not action:
            print("❌ Неизвестный пункт меню.")
            continue

        try:
            action(client)
        except ForemAPIError as e:
            print(f"❌ Ошибка API: {e}")
        except KeyboardInterrupt:
            print("\nПрервано пользователем.")
        except Exception as e:
            print(f"💥 Непредвиденная ошибка: {e}")


if __name__ == "__main__":
    main()