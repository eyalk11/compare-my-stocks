import logging
import sys


def confirm_yes_no(message, title="compare-my-stocks", default_no=True):
    """Ask the user a yes/no question via Qt QMessageBox when possible, else stdin.

    Returns True on Yes, False on No / no answer available.
    """
    if sys.platform == 'win32':
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox
            app = QApplication.instance()
            owns_app = False
            if app is None:
                app = QApplication([])
                owns_app = True
            buttons = QMessageBox.Yes | QMessageBox.No
            default = QMessageBox.No if default_no else QMessageBox.Yes
            try:
                ans = QMessageBox.question(None, title, message, buttons, default)
            finally:
                if owns_app:
                    app.quit()
            return ans == QMessageBox.Yes
        except Exception as e:
            logging.debug(f"QMessageBox prompt unavailable ({e}); falling back to stdin")

    try:
        reply = input(f"{message} [y/N]: ").strip().lower()
    except (EOFError, OSError):
        logging.warning("No stdin available to prompt; assuming No")
        return False
    return reply in ('y', 'yes')
