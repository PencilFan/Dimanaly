import pandas as pd
import numpy as np
import sympy as sp
from random import sample
from re import Pattern

# 以下是涉及到数据库database的程序,用于从数据库中提取数据

def get_database_columns(path='data_base.xlsx'):
    '''获取数据库的列名信息'''
    df=pd.read_excel(path)
    return df.columns
def get_varinfo(name,regex=False,flags=0,path='data_base.xlsx'):
    '''regex=False,通过完全匹配的方式查找数据库,
    一般用于get_dimmat()函数中自动创建DimVar数据类型'''
    '''regex=True,通过正则表达式的方式查找数据库,并返回找到的第一个结果
    (从左往右数的第一个,在此基础上再从上往下数的第一个)
    一般适用于用户自行创建DimVar数据类型的时候'''

    '''功能:在数据库中根据给定的名称(name)查找量纲变量的信息
    name可以是符符号、中英文名称、数值等数据库中存在的根艺信息'''

    '''返回内容:返回一个字典,其中包括:量纲字典(dimdic)、符号(symbol)、
    SI单位制下的数值(value_of_SI)'''
    ## 提取数据库中的数据并将确实值设定为np.nan,初始化量纲列(col_dim)、
    ## 符号列(col_symbol)、数值列(value_col),便于之后从这些列中提取信息
    df=pd.read_excel(path)
    df.fillna(value=np.nan,inplace=True)##更改,不知道为什么实验value=None会报错,说没有指定value或method的值
    col_dim=['L','M','T','I','Theta','n','J']
    col_symbol='symbol'
    col_value='value_of_SI'
    ## 获取目标变量所在的行索引(index)
    if not regex:
        row,_=np.where(df==name)#*在dataframe中查找特定元素的坐标
        index=df.index[row[0]]#*返回找到的第一个元素
    else:
        col_name=list(set(df.columns)-set(col_dim))#*得到量纲列之外的列
        df_name=df[col_name]#*得到除去量纲数据外的dataframe
        for col in col_name:
            '''遍历series[col_name]查找'''
            '''或许可以使用apply方法,但可能没法即时退出循环'''
            series_name=df_name[col]
            series_name=series_name.astype(str)#*转换为字符串类型,便于series.str.contains()的使用,
            #*但不知道为什么用copy=False没法就地更改
            index_bool=series_name.str.contains(name,flags=flags,regex=True)#*得到布尔索引
            index_name=series_name[index_bool].index#*根据布尔索引获取目标对象的索引
            if len(index_name)!=0:
                break#只有找到了数据库中从左往右数第一个匹配的列就返回
        index=index_name[0]#只提取第一个匹配列的从上往下数的第一个匹配元素
    ## 根据找到的行索引(index)结合初始时定义的列索引信息,提取查找对象的
    ## 量纲、符号、数值并打包成字典然后返回
    dimseries=df.loc[index,col_dim]
    symbol=df.loc[index,col_symbol]
    value=df.loc[index,col_value]
    result={'dimdic':dimseries.to_dict(),'symbol':symbol,'value_of_SI':value}
    #*如果没有找到则抛出错误
    return result
def operate_dimdic(dimvardic,regex=False):
    '''对传入的量纲变量字典(dimdic)进行操作(operate),
    方法: 将所有的量纲变量(对应字典中的键,也可以是字符,字符会被自动
    转换为量纲变量)的量纲乘上对应的指数(对应字典中的值)后再相乘

    返回: 返回上述运算结果的量纲(以pandas.series的数据形式,便于与变量对应),
    以及把dimvardic中的键全部变为量纲变量Dimvar后得到的量纲变量列表(dimvarlist),
    以方便用户查看与后续程序的调用'''
    dimseries=pd.Series(0,index=['L','M','T','I','Theta','n','J'])#*index与数据库中量纲列的命名与顺序是一致的
    dimvarlist=[]
    for key in dimvardic.keys():#*每次循环都要执行一次,keys()方法还是整个循环只执行一次
        ## 先把输入的数据全部整理为量纲变量(也就是将字符变量自动创建为量纲变量)
        if type(key)==DimVar:
            dimvar=key
        elif type(key)==str:
            dimvar=DimVar(use_database_byname=key,regex=regex)
        else:
            #*报错,输入的数据不符合要求
            pass
        ndimseries=pd.Series(dimvar.get_dimdic())#*得到每一个量纲变量的量纲序列(ndimseries)
        dimseries=dimseries+ndimseries*dimvardic[key]#*将量纲序列乘上对应的量纲指数后累加
        #*,其中利用了对series进行操作时索引自动对齐的特性
        dimvarlist.append(dimvar)#*将自动化过滤后的量纲变量装入量纲列表中
    return dimseries,dimvarlist

# 以上是涉及到数据库database的程序,用于从数据库中提取数据
# 以下是类型定义与数据解析提取部分

class DimVar:
    '''定义量纲变量类型,该类型绑定了量纲变量的量纲字典(dimdic),符号(symbol),
    SI单位下的数值(value_of_SI),字符符号和sympy符号(symbol,spsymbol),这些
    信息都可以通过内置的接口得到'''
    
    '''若use_database_byname参数取值,则代表使用该值在数据库中对应量纲信息,这个值可以是
    中英文名、符号、数字等任何数据库中能找到的信息(不包括列名),regex的布尔值代表是否使用正则表达式
    在数据库中查找,默认不采用正则表达式,以防止符号与英文名混淆(因为只返回第一个找到的信息)'''

    '''对于绑定的sympy符号变量属性,默认该变量的属性是正数(positive_autovar=True),
    因为这样便于对表达式进行化简,用户也可以继续添加其他属性'''
    def __init__(self,symbol=None,use_database_byname=None,regex=False,value_of_SI=None,
                 L=0.,M=0.,T=0.,I=0.,Theta=0.,n=0.,J=0.,positive_autovar=True,flags=0,**kwrds):
        self.name=use_database_byname#*用于判断是否使用数据库中的数据
        ## 通过数据库或用户自定义的方式生成量纲变量
        if self.name!=None:
            '''按数据库生成量纲字典'''
            ### 从数据库中提取量纲信息
            dic_info=get_varinfo(self.name,flags=flags,regex=regex)
            self.dimdic=dic_info['dimdic']
            ### 判断是否使用数据库中的符号
            if symbol==None:
                self.symbol=dic_info['symbol']#用于sympy输出格式
            else:
                self.symbol=symbol
            ### 判断是否使用数据库中的数值
            if value_of_SI==None:
                self.value_of_SI=dic_info['value_of_SI']
            else:
                self.value_of_SI=value_of_SI
        else:
            '''根据给定值生成量纲字典'''
            self.dimdic={'L':L,'M':M,'T':T,'I':I,'Theta':Theta,'n':n,'J':J}
            self.value_of_SI=value_of_SI
            self.symbol=symbol
        self.spsympy=sp.Symbol(self.symbol,positive=positive_autovar,**kwrds)#*根据字符符号及用户设定的变量属性生成sympy符号
    def get_dimdic(self):
        '''返回量纲字典'''
        return self.dimdic
    def get_dimseries(self):
        return pd.Series(self.dimdic)
    def get_symbol(self):
        '''返回字符符号'''
        return self.symbol
    def get_spsymbol(self):
        '''返回sympy符号'''
        return self.spsympy
    def get_value_of_SI(self):
        '''返回SI单位制下的值'''
        return self.value_of_SI
    def change_dimdic(self,dimdic,regex=False):
        '''对变量的量纲进行自定义修改
        方法:由多个已知变量的量纲生成新的量纲'''
        dimseries,_=operate_dimdic(dimdic,regex=regex)
        self.dimdic=dimseries.to_dict()
        return self.dimdic
    
## 数据提取部分
def get_dimmat(inputlist,regex=False,positive_autovar=True,flags=0,**kwrds):##更改,新增',positive_autovar=True,**kwrds'
    '''
    输入:由Dimvar数据与字符数据构成的一个单轴列表,
    列表中的字符数据能被自动转换为Dimvar数据,自动转换的过程可以选择是否使用正则表达式
    返回:提取到的dataframe类型的量纲矩阵(dimmat)以及自动生成的dimvar类型的列表(dimvarlist)
    '''
    dimvarlist=[]
    dimvarmat=[]
    row_name=[]
    for input in inputlist:
        '''
        遍历输入的变量列表,产生用于生成dimvarmat的列表,
        列表中的元素是由量纲与数值构成的字典,
        还有用于产生dimvarmat的行名列表(row_name)
        '''
        ## 检查输入列表中的变量,将字符数据转换为dimvar数据,
        ## 将所有的dimvar数据添加进dimvarlist列表中
        type_input=type(input)
        if type_input==DimVar:
            dimvar=input
            dimvarlist.append(dimvar)
        elif type_input==str or type_input==Pattern:
            dimvar=DimVar(use_database_byname=input,regex=regex,positive_autovar=positive_autovar,flags=flags,**kwrds)#*使用的符号应该是数据库中对应的符号
            dimvarlist.append(dimvar)
        else:
            pass#*其他情况则报错
        ## 将量纲数据和数值数据打包成一个字典并添加进dimvarmat列表中
        ## 同时根据变量符号生成列名列表(row_name)
        dicadd={'value_of_SI':dimvar.get_value_of_SI()}#*添加数据行
        dimvardic={**dimvar.get_dimdic(),**dicadd}#*生成新字典,参考ChatGPT
        dimvarmat.append(dimvardic)
        row_name.append(dimvar.get_symbol())#*行名必须是字符类型
    dimmat=np.transpose(pd.DataFrame(dimvarmat,index=row_name))#*创建dataframe类型的数据并取转置
    return dimmat,dimvarlist

# 以上是类型定义与数据解析提取部分
# 以下是数学求解部分

def get_indegroup(dimmat):
    '''
    返回:最大线性无关组矩阵(indegroup)和其他剩余向量构成的矩阵(othergroup)
    indegroup与othergroup都是dataframe类型的数据'''
    dimmat_novalue=dimmat.drop('value_of_SI')#首先取出数值行,注意不能使用inplace=True,这样在函数外面也会跟着改
    ## 通过QR分解找到极大线性无关组的列索引从而得到indegroup
    _,mat_R=np.linalg.qr(dimmat_novalue)
    _,col_num=np.shape(dimmat_novalue)
    #*因为受机器精度的限制有些实际为零的元素计算结果是一个很小的非零数
    threshold=np.average(np.abs(mat_R))/1e3#*设置可以视为零的阈值,/1e3是一个经验参数
    col_index_tmp=np.argmax(np.abs(mat_R)>threshold,axis=1)#*找到每行第一个不为零元素所对应的列索引
    ### 若有一行上的元素都小于阈值,那么将得到改行第一个元素所在的列序号也就是0,
    ### 但这并不是我们要找的极大线性无关组中的成员,
    ### 因此需要用下面的循环判断每一行中第一个大于零的那个值是否真的大于零,
    ### 筛选出真正的极大线性无关组所对应的列号并放入col_index列表中
    n=0
    col_index=[]
    for col in col_index_tmp:
        if np.abs(mat_R[n,col])>threshold:#注意是用绝对值与阈值(threshold)比较
            col_index.append(col)
        n+=1
    indegroup=dimmat_novalue.iloc[:,np.unique(col_index)]#使用unique清理掉重复项(基础是极大线性无关组的选取是正确的)
    ## 通过集合得到除indegroup外剩下的数据,即othergroup
    col_all=set(range(col_num))
    col_other=list(col_all-set(col_index))#找到出极大线性无关组外其他列的索引
    othergroup=dimmat_novalue.iloc[:,col_other]
    return indegroup,othergroup

def get_PiIndex(indegroup,othergroup):
    '''
    返回:Pi的指数表达式列表
    列表的元素是字典,每一个字典的键是极大线性无关组中的变量符号与其中一个其他组中的变量符号
    值是这些变量的量纲指数,每一个字典对应着一个无量纲量Pi
    '''
    ## 获取indegroup、othergroup的列名、
    ## indegroup的行列数、随机数种子、用于开启循环迭代的方阵A
    indegroup_columns=indegroup.columns
    othergroup_columns=othergroup.columns
    nrow,ncol=np.shape(indegroup)
    rowlist=range(ncol)
    population=range(nrow)#*生成随机数产生的范围
    A=indegroup.iloc[rowlist,:]#*初始化方阵
    A=A.astype('float')#*转换数据类型便于数学操作
    ## 构造利用numpy.linalg.solve()求解线性方程组的A、B矩阵
    while np.linalg.matrix_rank(A)<ncol:
        '''使用随机数选取满秩矩阵'''
        rowlist=sample(population,ncol)
        A=indegroup.iloc[rowlist,:]
        A=A.astype('float')#对每次新生成的A也要即使转换数据类型以方便循环条件判断计算矩阵的秩,这里一直被忽略,所以debug了很久
    B=othergroup.iloc[rowlist,:]#*对应A选取的列相应地选取B
    B=B.astype('float')#与A同理
    ## 遍历othergroup的每一列,求解量纲指数、生成字典并添加进列表中
    index_list=[]#*量纲指数列表
    for col in othergroup_columns:
        X=np.linalg.solve(A,B[col])
        key=np.concatenate((indegroup_columns,[col]))#字典的键
        value=np.concatenate((X,[-1]))#字典的值
        index_dic=dict(zip(key,value))#将键与值组合成字典
        index_list.append(index_dic)
    return index_list

## 以上是数学求解部分
## 以下是数据整理输出以及主类DimFormula

def get_Pilist(index_list):
    '''返回:一个由无量纲的符号表达式构成的列表'''
    Pilist=[]
    ## 将index_list列表内的每一字典中的符号与指数相乘后得到一个符号表达式
    ## 将这些符号表达式装进列表中并返回
    for dic in index_list:
        Pi=sp.S(1)
        for key in dic.keys():
            symbol=sp.Symbol(key)
            index=dic[key]
            tmp=symbol**index
            Pi=Pi*tmp
        Pilist.append(sp.nsimplify(Pi))#简化指数(如p**1.0/r**1.0),参考ChatGPT
    return Pilist

def get_formula(Pilist):
    '''根据Pilist的长度确定公式的输出形式'''
    length=len(Pilist)
    function=sp.Function('\Pi')
    if length==1:
        formula=sp.Eq(Pilist[0],sp.Symbol('C'))
    elif length==2:
        formula=sp.Eq(Pilist[0],function(Pilist[1]))
    else:
        formula=sp.Eq(function(*Pilist),0)#使用*Pilist创建未知数目的多个自变量,来自ChatGPT
    return formula

def subs_symbol(symbol,dimvarlist,to_value=True):##更改
    '''
    功能:将输入的symbol中的符号全部替换为dimvarlist中定义的sympy符号(只替换非None的符号)或数值,
    替换哪一个由参数to_value决定,默认替换数值,这样对用户更方便
    返回:替换后得到的新的符号列表(newsymbol_list)
    '''
    for dimvar in dimvarlist:
        if to_value==False:
            symbol=symbol.subs(dimvar.get_symbol(),dimvar.get_spsymbol())
        elif to_value==True:
            value=dimvar.get_value_of_SI()
            if value and (not np.isnan(value)):#*此处判断写得有点长,起初用value!=None,但不能识别nan
                symbol=symbol.subs(dimvar.get_spsymbol(),value)#*注意这里若使用get_symbol()将无法替换
                #*因为get_spsymbol()得到的是sympy符号与get_symbol()得到的字符符号是不同的
        else:
            #报错
            pass
    return symbol

def subs_symbol_list(symbol_list,dimvarlist,to_value=True):##更改
    '''
    功能:将输入的symbol_list中的符号全部替换为
    dimvarlist中定义的sympy符号(只替换非None的符号)或数值,
    替换哪一个由参数to_value决定,默认替换数值,这样对用户更方便
    返回:替换后得到的新的符号列表(newsymbol_list)
    '''
    newsymbol_list=[]
    for nsymbol in symbol_list:
        newsymbol=nsymbol
        for dimvar in dimvarlist:
            if to_value==False:
                newsymbol=newsymbol.subs(dimvar.get_symbol(),dimvar.get_spsymbol())
            elif to_value==True:
                value=dimvar.get_value_of_SI()
                if value and (not np.isnan(value)):#*此处判断写得有点长,起初用value!=None,但不能识别nan
                    newsymbol=newsymbol.subs(dimvar.get_spsymbol(),value)#*注意这里若使用get_symbol()将无法替换
                    #*因为get_spsymbol()得到的是sympy符号与get_symbol()得到的字符符号是不同的
            else:
                #报错
                pass
        newsymbol_list.append(newsymbol)
    return newsymbol_list

class DimFormula:
    def __init__(self,*inputlist,positive_autovar=True,regex=False,flags=0,**kwrds):
        dimmatlist=[]
        dimvarset=set()#使用集合以过滤重复项,##更改,新增
        inputall_set=set()
        old_Pilist=[]##更改
        self.index_list=[]
        self.indegroup=[]
        self.othergroup=[]
        for input in inputlist:
            ## 走求解流程然后获得相关数据
            dimmat,dimvarlist=get_dimmat(input,regex=regex,positive_autovar=positive_autovar,flags=flags,**kwrds)##更改,新增',positive_auovar=True,**kwrds',dimmat,dimvatlist=
            indegroup,othergroup=get_indegroup(dimmat)
            index_list=get_PiIndex(indegroup,othergroup)
            Pilist=get_Pilist(index_list)
            ## 处理获得的数据然后将他们装进对应的列表或集合中
            dimvarset.update(dimvarlist)#用update方法向集合中添加多个元素
            inputall_set.update(input)
            self.indegroup.append(indegroup)
            self.othergroup.append(othergroup)
            self.index_list+=index_list#只能使用加号,若用append会产生嵌套列表
            old_Pilist+=Pilist##更改
            dimmatlist.append(dimmat)
        self.inputall_list=list(inputall_set)
        ## 对dimmat进行合并、去重、重命名索引(行名)、去NaN、去零的数据整理与清洗操作
        dimmatall=pd.concat(dimmatlist,axis=1)#*将dimmatlist列表中的dataframe类型的dimmat数据合并为一个dataframe数据
        dimmatall=dimmatall.loc[:,~dimmatall.columns.duplicated()]#合并列名重复的列,参考ChatGPT
        dimmatall.reindex(get_database_columns(),copy=False)#*不知为何此处的copy=False就可以实现就地更改
        dimmatall=dimmatall[~(dimmatall==0).all(axis=1)]#清除掉全为零的行
        ## 得到该类绑定的dimmat以及由之得到的dimvarlist、Pilist、formula
        self.dimmat=dimmatall
        self.dimvarlist=list(dimvarset)#转换为列表类型方便下标访问
        self.Pilist=subs_symbol_list(old_Pilist,self.dimvarlist,to_value=False)#将Pilist中的符号全部赋予用户定义的属性,默认为positive##更改
        self.formula=get_formula(self.Pilist)
        ## 生成一个便于用户查询的量纲变量列表字典,字典的键是变量的符号,值为变量数据
        keylist=[]
        for dimvar in self.dimvarlist:
            key=dimvar.get_symbol()
            keylist.append(key)
        self.dimvardic=dict(zip(keylist,dimvarlist))

    def get_dimvardic(self):
        '''一般在用户提取特定量纲的信息时适用'''
        return self.dimvardic
    def get_dimvarlist(self):
        '''一般在数值替换时使用'''
        return self.dimvarlist
    def get_inputall_list(self):
        return self.inputall_list
    def get_dimmat(self):
        return self.dimmat
    def get_indegroup(self):
        return self.indegroup
    def get_othergroup(self):
        return self.othergroup
    def get_index_list(self):
        return self.index_list
    def get_Pilist(self):
        return self.Pilist
    def check_freedom(self):
        '''用于检查输出公式的自由度与全局自由度是否匹配以判断公式的正确性'''
        ## 将输入的所有列表串联然后走一遍求解程序,得到全局无量纲式的列表(allPilist)
        ## 以及由此得到的全局公式(allformula),比较allPilist和Pilist的长度以确定公式的自由度是否正确
        dimmat_all,_=get_dimmat(self.inputall_list)
        indegroup_all,othergroup_all=get_indegroup(dimmat_all)
        indexlist_all=get_PiIndex(indegroup_all,othergroup_all)
        self.__allPilist=get_Pilist(indexlist_all)
        self.__allformula=get_formula(self.__allPilist)
        if len(self.Pilist)==len(self.__allPilist):
            print('the degree of freedom is correct')
        elif len(self.Pilist)>len(self.__allPilist):
            print('the degree of freedom is more')
        else:
            print('the degree of freedom is less')
    def get_formula(self):
        return self.formula
    def get_formula_aboutallinput(self):
        return self.__allformula
    def get_formulafor(self,var,choose_result=0):
        '''
        得到关于某一变量的公式
        公式的形式可能有很多种,这里默认选取第一种,
        因为第一种往往是最简单的也是最符合实际的
        '''
        ## 首先将字符类型的目标变量转换为Dimvar类型
        if type(var)==str:
            dimvar=self.dimvardic[var]
        else:
            dimvar=var
        ## 求解方程然后得到新的表达式
        solutions=sp.solve(self.formula,dimvar.get_spsymbol())#解方程并得到结果等式的右部分
        rhs=solutions[choose_result]
        expr=sp.Eq(dimvar.get_spsymbol(),rhs)#合成等式
        self.solutions=solutions#将解存为属性,方便用户查看
        return sp.simplify(expr)
    def get_formulavalue(self):##更改
        Pilist_value=subs_symbol_list(self.Pilist,self.dimvarlist,to_value=True)
        formulavalue=get_formula(Pilist_value)
        return formulavalue
    
# 以上是数据整理输出以及主类DimFormula
# 以下是判断公式正确性的部件

def is_true(dimvardic,regex=False):
    '''
    功能:检查公式的正确性
    输入:量纲字典,它的键是量纲变量或字符,它的值是该变量所对应的量纲指数
    对于输入的字符,可选择使用正则表达式形式或全匹配形式将其自动转换为dimvar类型
    '''
    dimseries,dimvarlist=operate_dimdic(dimvardic,regex=regex)
    if len(dimseries[dimseries!=0])==0:
        ## 当返回的量纲序列(dimseries)中的量纲指数全为零时则公式在量纲上正确
        print('the formula is dimensionally correct')
    else:
        print('the formula is wrong')
    return dimseries,dimvarlist

# 以上是判断公式正确性的部件