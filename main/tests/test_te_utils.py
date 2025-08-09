from main.te_utils import parse_trade_text
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def test_parse_trade_text():
    test_string_1 = "Ata added 1x ArmaLite M-15A4 to the trade."
    test_string_2 = "Ata added 913x ArmaLite M-15A4, 110929x Enfield SA-80, 2023x Dual 92G Berettas, 11x Type 98 Anti Tank, 12x MP3 Player, 1x RS232 Cable to the trade."
    test_string_3 = "Ata2123aax2as12 added 913x ArmaLite M-15A4, 110929x Enfield SA-80, 2023x Dual 92G Berettas, 11x Type 98 Anti Tank, 12x MP3 Player, 1x RS232 Cable to the trade."
    test_string_4 = "LDOC added  1x Bottle of Pumpkin Brew, 29x Bottle of Tequila, 49x Bottle of Wicked Witch, 21x Can of Crocozade, 103x Can of Damp Valley to the trade."

    logger.debug(parse_trade_text(test_string_4))
    assert parse_trade_text(test_string_1) == ('Ata', ['ArmaLite M-15A4'], [1])

    assert parse_trade_text(test_string_2) == ('Ata', [
        'ArmaLite M-15A4', 'Enfield SA-80', 'Dual 92G Berettas', 'Type 98 Anti Tank', 'MP3 Player', 'RS232 Cable'], [913, 110929, 2023, 11, 12, 1])
    assert parse_trade_text(test_string_3) == ('Ata2123aax2as12', [
        'ArmaLite M-15A4', 'Enfield SA-80', 'Dual 92G Berettas', 'Type 98 Anti Tank', 'MP3 Player', 'RS232 Cable'], [913, 110929, 2023, 11, 12, 1])
    assert parse_trade_text(test_string_4) == ('LDOC', ['Bottle of Pumpkin Brew', 'Bottle of Tequila',
                                                        'Bottle of Wicked Witch', 'Can of Crocozade', 'Can of Damp Valley'], [1, 29, 49, 21, 103])
