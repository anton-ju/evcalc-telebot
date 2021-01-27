FROM python:3.6

WORKDIR /home/ant/python-projects/evcalc-telebot

COPY requirements.txt ./
RUN apt-get update 
RUN apt-get install -y --no-install-recommends git
RUN pip install Cython
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "./evcalcbot.py"]
