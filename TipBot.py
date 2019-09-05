from selenium.common.exceptions import WebDriverException
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from Match import Match
import os
from twilio.rest import Client


class TipBot:
    def __init__(self):
        self.sendWhatsApp('++++++ Kicktip-Soccer-Bot started ++++++')
        self._initialize_headless_browser()

    def _initialize_headless_browser(self):
        opts = Options()
        opts.headless = True
        try:
            self.browser = Chrome(options=opts)
        except WebDriverException:
            self.browser = Chrome(executable_path=os.environ['CHROMEDRIVER'], options=opts)


    def _authenticate_to_kicktipp(self):
        self.browser.get('https://www.kicktipp.de/djk-labbeck/profil/login')

        self.browser.find_element_by_id("kennung").send_keys(os.environ['EMAIL'])
        self.browser.find_element_by_id("passwort").send_keys(os.environ['PASSWORD'])
        self.browser.find_element_by_name("submitbutton").click()

    def _go_to_tip_submission(self):
        self.browser.get("https://www.kicktipp.de/djk-labbeck/tippabgabe")

    def _get_match_list_of_current_gameday(self):
        most_recent_game_day_matches = []

        # Scrape the html to gather the required information
        table = self.browser.find_element_by_xpath("//table[@id='tippabgabeSpiele']")

        for row in table.find_elements_by_xpath(".//tr"):
            data_of_table_row = row.find_elements_by_xpath(".//td")
            if len(data_of_table_row) >= 6:
                match = Match(home_team=data_of_table_row[1].text,
                              away_team=data_of_table_row[2].text,
                              odd_home_team_wins=float(data_of_table_row[4].text.replace(",", ".")),
                              odd_draw=float(data_of_table_row[5].text.replace(",", ".")),
                              odd_away_team_wins=float(data_of_table_row[6].text.replace(",", ".")),
                              table_data_html=data_of_table_row[3]
                              )
                most_recent_game_day_matches.append(match)

        return most_recent_game_day_matches

    def _tip_each_match(self, match_list):
        for match in match_list:
            self._fill_tip_input_for_match(match)
        msg = self.getMsgForMatches(match_list)
        self.sendWhatsApp(msg)

    def _fill_tip_input_for_match(self, match):
        tip_tuple = self._get_expected_goals_for_match_as_tuple(match)
        inputs_fields = match.table_data_html.find_elements_by_xpath(".//input")
        if len(inputs_fields) >= 2:
            inputs_fields[1].clear()
            inputs_fields[1].send_keys(tip_tuple[0])
            inputs_fields[2].clear()
            inputs_fields[2].send_keys(tip_tuple[1])

    def _get_expected_goals_for_match_as_tuple(self, match):
        # negative => Home team wins
        # positive => away team wins
        diff = match.odd_home_team_wins - match.odd_away_team_wins

        if diff < -2:
            return 2, 0
        if diff < -1:
            return 2, 1
        if diff < 0:
            return 1, 0
        if diff > 2:
            return 0, 2
        if diff > 1:
            return 1, 2
        if diff > 0:
            return 1, 2
        else:
            return 2, 1


    def _submit_all_tips(self):
        self.browser.find_element_by_name("submitbutton").click()

    def tip_all_matches_and_submit(self):
        self._authenticate_to_kicktipp()
        self._go_to_tip_submission()
        most_recent_game_day_matches = self._get_match_list_of_current_gameday()
        self._tip_each_match(most_recent_game_day_matches)
        self._submit_all_tips()
        self.browser.close()

    def sendWhatsApp(self, msg):
        account_sid = os.environ['TWILIO_ACCOUNT_SID']
        auth_token = os.environ['TWILIO_AUTH_TOKEN']
        client = Client(account_sid, auth_token)

        message = client.messages.create(
                                    from_='whatsapp:+14155238886',
                                    body=msg,
                                    to='whatsapp:+4917647704597'
                                )

    def getMsgForMatches(self, match_list):
        msg = 'Kicktip-Soccer-Bot hat folgende Partien erfolgreich getippt:' + '\n'
        for match in match_list:
            msg += '\n'
            tupel = self._get_expected_goals_for_match_as_tuple(match)
            msg += str(tupel[0]) + ' ' + match.home_team + ' (' + str(match.odd_home_team_wins) + ')' + '\n'
            msg += str(tupel[1]) + ' ' +  match.away_team + ' (' + str(match.odd_away_team_wins) + ')' + '\n'
        return msg



if __name__ == "__main__":
    bot = TipBot()
    bot.tip_all_matches_and_submit()
