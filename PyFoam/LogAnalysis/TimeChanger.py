"""Class that notifies others of its changed time """

class TimeChanger:
    """Mixin the sends the special time to other classes"""

    def __init__(self):
        self._listener=[]

    def addTimeListener(self,listener):
        self._listener.append(listener)

    def sendTime(self):
        for listener in self._listener:
            listener.timeChanged()
        self.parent.setTime(self.getTime())
