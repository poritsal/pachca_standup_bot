# Standup Bot for Pachca

Standup Bot - это приложение на базе FastAPI, предназначенное для проведения стендап-встреч в групповых чатах. Бот собирает отчеты от пользователей, отслеживает их доступность и управляет различными настройками, связанными с процессом стендапов.

## Возможности

    Сбор стендап-отчетов от пользователей в чате.
    Отправка напоминаний и сбор ответов.
    Отслеживание пользователей, которые болеют или находятся на отдыхе.
    Настройка специфических для чата параметров, таких как руководители, расписание и временные ограничения для стендапов.
    Предоставление команд для управления поведением и настройками бота.

## Установка

 1. Клонируйте репозиторий:
 ```
git clone https://github.com/yourusername/standup-bot.git
cd standup-bot 
 ```

2. Создайте виртуальное окружение и активируйте его:

```
python -m venv env
source env/bin/activate  # В Windows используйте env\Scripts\activate
```

3. Установите необходимые пакеты:

```
pip install -r requirements.txt
```

4. Создайте файл .env в корневой директории проекта и добавьте туда токен доступа и ID вашего бота:
```
access_token=your_access_token
bot_id=your_bot_id
```
## Использование

1. Запустите сервер FastAPI:
```
uvicorn main:app --reload
```

2. Установите и настройте Ngrok для проброса локального сервера в интернет:

- Скачайте и установите Ngrok с официального сайта.

- Запустите Ngrok и пробросьте порт 8000:
    ```
    ngrok http 8000
    ```
- Скопируйте выданный Ngrok URL и настройте бот для отправки вебхуков на этот URL (например, https://<your_ngrok_url>/webhook). Это можно сделать во вкладке "Исходящий Webhook" в меню чат-бота в Пачке.

3. Бот автоматически начнет управлять стендапами согласно настроенному расписанию.

## Команды
```
/sick - Отметить себя как болеющего.
/rest - Отметить себя как отдыхающего.
/return - Отметить себя как доступного для участия.
/heads @nickname1 @nickname2 ... - Назначить руководителей стендапа в чате.
/schedule день1 время1 день2 время2 ... - Установить расписание стендапов.
/limit минуты - Установить временное ограничение для стендапов.
/pause - Приостановить или возобновить стендапы в чате.
/help - Получить информацию о доступных командах.
/delete - Удалить все настройки стендапов для чата.
```
## Подготовка сервера
1. git
```
sudo apt-get update
sudo apt-get install git
```

2. docker
Можно воспользоваться инструкцией: https://docs.docker.com/engine/install/ubuntu/
или скопировать код ниже
```
sudo apt-get update
sudo apt-get install ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update

sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```
3. Переход в папку проекта
```
cd pachca_standup_bot/
``` 
4. Запуск приложения
```
docker build . --tag fastapi_app && docker run -p 80:80 fastapi_app
```
