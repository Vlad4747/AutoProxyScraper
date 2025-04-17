# AutoProxyScraper

AutoProxyScraper — это веб-приложение для автоматического поиска, проверки и отображения прокси-серверов в удобной таблице.

## Установка без Docker

Чтобы установить AutoProxyScraper без использования Docker, выполните следующие шаги:

1. **Клонируйте репозиторий**:
   ```bash
   git clone https://github.com/Vlad4747/AutoProxyScraper.git
   ```

2. **Перейдите в директорию проекта**:
   ```bash
   cd AutoProxyScraper
   ```

3. **Установите зависимости**:
   Убедитесь, что у вас установлен Python и pip. Затем выполните:
   ```bash
   pip install -r requirements.txt
   ```

4. **Запустите приложение**:
   ```bash
   python main.py
   ```

5. **Доступ к приложению**:
   После запуска приложения, вы сможете получить доступ к веб-интерфейсу по адресу `http://localhost:5000`.

## Установка с Docker

Если вы предпочитаете использовать Docker, выполните следующие шаги:

1. **Клонируйте репозиторий**:
   ```bash
   git clone https://github.com/Vlad4747/AutoProxyScraper.git
   ```

2. **Перейдите в директорию проекта**:
   ```bash
   cd AutoProxyScraper
   ```

3. **Постройте Docker-образ**:
   ```bash
   docker build -t autoproxyscraper .
   ```

4. **Запустите контейнер**:
   ```bash
   docker run -d --name autoproxyscraper -p 5000:5000 autoproxyscraper
   ```

5. **Доступ к приложению**:
   После запуска контейнера, вы сможете получить доступ к веб-приложению по адресу `http://localhost:5000`.

## Вклад

Если вы хотите внести свой вклад в проект, пожалуйста, создайте форк репозитория и отправьте пулл-реквест с вашими изменениями.
