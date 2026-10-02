from common import H, alerts_html, get_state

S = get_state()
H(alerts_html(S["res"], True))
