from abc import abstractmethod, ABCMeta
import dataframe

class mediaCollection(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def initDataframe(self,index):
        pass

    @abstractmethod
    def getMedia(self,index):
        pass

    @abstractmethod
    def dropMedia(self,index):
        pass

    @abstractmethod
    def upsertMedia(self,arr):
        pass



class audioCollection(mediaCollection):
    __metaclass__ = ABCMeta

    def __init__(self,name,data=None,mongoDict=None,metadataParse=None):
        self.name = name
        self.data = data
        self.mongoDict = mongoDict
        self.metadataParse = metadataParse
        self.size = 0

        self.initDataframe()

    def initDataframe(self):
        if self.data is not None:
            self.data, self.dataFrame = dataframe.fromAudioArray(self.data,self.metadataParse)
        elif self.mongoDict is not None:
            self.data, self.dataFrame = dataframe.fromMongoQuery(self.mongoDict,self.metadataParse)
        else:
            raise ValueError("Variable 'data' is None but no other data source supplied.")

        self.size = len(self.data.keys())


    def getDataFrame(self,condition=None):
        if condition is None:
            return self.dataFrame
        else:
            return self.dataFrame[condition]

    def setSamplingResolution(self,timeStep=None,freqStep=None):
        if timeStep is not None:
            self.timeStep = timeStep
        if freqStep is not None:
            self.freqStep = freqStep


    def getMedia(self,condition=None):
        if condition is None:
            indArr =  list(self.dataFrame["akey"])
        else:
            indArr = list(self.dataFrame[condition]["akey"])

        return [self.data[key] for key in indArr]

    def dropMedia(self,condition=None):
        self.dataFrame, keyArr = dataframe.dropData(self.dataFrame,condition)
        for key in keyArr:
            del self.data[key]

    def upsertMedia(self,arr):
        upserted, self.dataFrame = dataframe.upsertData(self.dataFrame,arr,self.metadata)
        for key in upserted:
            self.data[key] = upserted[key]









