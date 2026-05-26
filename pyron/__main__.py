import sys


def main():
    if "--gui" in sys.argv:
        from pyron.gui.app import launch
        launch()
    else:
        from pyron.cli.terminal import main
        main()


if __name__ == "__main__":
    main()
