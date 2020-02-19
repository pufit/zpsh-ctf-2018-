import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import *
import time
import threading
from gspread.exceptions import RequestError


class GoogleSheet(threading.Thread):
    def __init__(self):
        super(GoogleSheet, self).__init__(target=self.tick)
        self.creds = ServiceAccountCredentials.from_json_keyfile_name(CLIENT_SECRET, SCOPE)
        self.client = gspread.authorize(self.creds)
        self.sheet = self.client.open(SHEET_NAME).sheet1

        self.update_delay = UPDATE_DELAY
        self.table = []

        self.start()
        self.win = None

    def tick(self):
        while True:
            self.update()
            time.sleep(self.update_delay)

    def update(self):
        try:
            self.table = list(zip(self.get_commands_name(), self.get_commands_score()))
        except RequestError:
            print('Sheets dropped connection. Reconnect')
            self.creds = ServiceAccountCredentials.from_json_keyfile_name(CLIENT_SECRET, SCOPE)
            self.client = gspread.authorize(self.creds)
            self.sheet = self.client.open(SHEET_NAME).sheet1
            self.update()

    def get_commands_name(self):
        i = 0
        while True:
            result = self.sheet.cell(COMMANDS_NAME_START[0] + i, COMMANDS_NAME_START[1]).value
            if result != '':
                yield result
                i += 1
            else:
                raise StopIteration()

    def get_commands_score(self):
        i = 0
        while True:
            result = self.sheet.cell(COMMANDS_SCORE_START[0] + i, COMMANDS_SCORE_START[1]).value
            if result != '':
                yield result
                i += 1
            else:
                raise StopIteration()

    def set_score(self, team, points):
        self.win = team
        team_index = list(map(lambda x: x[0], self.table)).index(team) + COMMANDS_NAME_START[0]
        self.sheet.update_cell(team_index, COMMANDS_SCORE_START[1], points)
