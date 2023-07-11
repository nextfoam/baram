#  ICE Revision: $Id$ 
"""A ring-buffer data structure"""

class RingBuffer(object):
    """A data structure that stores a number N of elements. The
    N+1-element overwrites the first and so on ...."""

    def __init__(self,nr=1000):
        """
	:param nr: Number of elements to store
	"""
        self.nr=nr
        self.list=[None]*nr
        self.point=0
        self.full=False

    def insert(self,dings):
        """ Inserts am element into the ring-buffer
        """
        #        print "Inserting at",self.point,":",dings
        self.list[self.point]=dings
        self.point+=1
        if self.point==self.nr:
            self.point=0
            self.full=True
        
    def last(self):
        """:return: the latest element in the buffer, None if
        nothing was inserted into the buffer"""
        if self.point>0:
            return self.list[self.point-1]
        elif self.full:
            return self.list[-1]
        else:
            return None

    def dump(self):
        """:return: A list with all the values in the ring buffer in the correct order
	(starting with the oldest)"""
        result=[]

        if self.full:
            for i in range(self.point,self.nr):
                result+=self.list[i]+"\n"
        for i in range(self.point):
            result+=self.list[i]+"\n"
            
        return result
