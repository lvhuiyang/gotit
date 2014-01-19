#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

import web
from web.contrib.template import render_jinja

from addons import get_old_cet, get_book
from addons.get_CET import CET
from addons.zfr import ZF, Login
from addons.autocache import memorize
from addons import config
from addons.config import index_cache, debug_mode, sponsor, zheng_alert
from addons.RedisStore import RedisStore
from addons.utils import init_redis, get_score_jidi
from addons import errors

#import apis
import manage
from forms import cet_form, xh_form, login_form

# debug mode
web.config.debug = debug_mode

urls = (
    '/', 'index',
    '/zheng', 'zheng',
    '/more/(.+)', 'more',
    '/years', 'years',
    '/score', 'score',
    '/cet', 'cet',
    '/cet/old', 'cet_old',
    '/libr', 'libr',
    #'/api', apis.apis,
    '/manage', manage.manage,
    '/contact.html', 'contact',
    '/notice.html', 'notice',
    '/help/gpa.html', 'help_gpa',
    '/comment.html', 'comment',
    '/donate.html', 'donate',
    '/root.txt', 'ttest',
    '/status', 'status',
)

# main app
app = web.application(urls, globals(),autoreload=False)


# session
if web.config.get('_session') is None:
    session = web.session.Session(app, RedisStore(), {'count': 0, 'xh':False})
    web.config._session = session
else:
    session = web.config._session

# render templates
render = render_jinja('templates', encoding='utf-8',globals={'context':session})

# 首页索引页
class index:

    @memorize(index_cache)
    def GET(self):
        return render.index(alert=zheng_alert)


# 成绩查询
class zheng:

    def GET(self):

        try:
            zf = ZF()
            time_md5 = zf.pre_login()
        except errors.ZfError, e:
            return render.serv_err(err=e.value)
        session['time_md5'] = time_md5
        # get checkcode
        r = init_redis()
        checkcode = r.hget(time_md5, 'checkcode')

        return render.zheng(alert=zheng_alert, checkcode=checkcode)

    def POST(self):
        content = web.input()
        session['xh'] = content['xh']
        t = content['type']
        time_md5 = session.time_md5

        try:
            zf = Login()
            zf.login(time_md5, content)
            __dic = {
                    '1': zf.get_score,
                    '2': zf.get_kaoshi,
                    '3': zf.get_kebiao,
                    '4': zf.get_last_kebiao,
                    }
            if t not in __dic.keys():
                return render.alert_err(error='输入不合理', url='/zheng')
            return render.result(table=__dic[t]())
        except errors.PageError, e:
            return render.alert_err(error=e.value, url='/zheng')



class more:
    """连续查询 二次查询
    """
    def GET(self, t):
        if session['xh'] is False:
            raise web.seeother('/zheng')
        try:
            __dic1 = { # need xh
                    'oldcet':get_old_cet,
                    }
            if t in __dic1.keys():
                return render.result(table=__dic1[t](session['xh']))

            elif t=='score':
                score, jidi=get_score_jidi(session['xh'])
                return render.result(table=score, jidian=jidi)
            #elif t=='morekb':
            zf = Login()
            __dic = { # just call
                    'zheng': zf.get_score,
                    'kaoshi': zf.get_kaoshi,
                    'kebiao': zf.get_kebiao,
                    'lastkebiao': zf.get_last_kebiao,
                    }
            if t in __dic.keys():
                zf.init_after_login(session['time_md5'], session['xh'])
                return render.result(table=__dic[t]())
            raise web.notfound()
        except (AttributeError, TypeError):
            raise web.seeother('/zheng')

class years:

    def GET(self):

        try:
            zf = Login()
            zf.init_after_login(session['time_md5'], session['xh'])
            years=zf.more_kebiao()
            return render.years_result(years=years)
        except (AttributeError, TypeError):
            raise web.seeother('/zheng')

    def POST(self):

        zf = Login()
        zf.init_after_login(session['time_md5'], session['xh'])
        return 'ok'


# cet

class cet:

    @memorize(index_cache)
    def GET(self):
        form = cet_form()
        if config.baefetch:
            return render.cet_bae(form=form)
        else:
            return render.cet(form=form)
        # return render.cet_raise()

    def POST(self):
        form = cet_form()
        if not form.validates():
            return render.cet(form=form)
        else:
            zkzh = form.d.zkzh
            name = form.d.name
            name = name.encode('utf-8')
            items = ["学校","姓名","阅读", "写作", "综合",
                    "准考证号", "考试时间", "总分", "考试类别",
                    "听力"]
            cet = CET()
            res = cet.get_last_cet_score(zkzh, name)
            return render.result_dic(items=items, res=res)


class cet_old:
    """
    往年cet成绩查询
    """
    @memorize(index_cache)
    def GET(self):
        form=xh_form
        title='往年四六级成绩'
        return render.normal_form(title=title, form=form)
    def POST(self):
        form = xh_form()
        title='往年四六级成绩'
        if not form.validates():
            return render.normal_form(title=title, form=form)
        else:
            xh = form.d.xh
            session['xh']=xh
        table=get_old_cet(xh)
        return render.result(table=table)


class libr:
    """
    图书馆相关
    """
    @memorize(index_cache)
    def GET(self):
        form=login_form
        title='图书馆借书查询'
        return render.normal_form(title=title, form=form)

    def POST(self):
        form=login_form()
        title='图书馆借书查询'
        if not form.validates():
            return render.normal_form(title=title,form=form)
        else:
            xh, pw=form.d.xh, form.d.pw
            session['xh']=xh
        table=get_book(xh,pw)
        return render.result(table=table)


# contact us

class status:

    def GET(self):
        return 'status'


class contact:

    """contact us page"""
    @memorize(index_cache)
    def GET(self):
        return render.contact()

# notice


class notice:

    @memorize(index_cache)
    def GET(self):
        return render.notice()


# 全部成绩
class score:

    @memorize(index_cache)
    def GET(self):
        form = xh_form()
        return render.score(form=form)

    def POST(self):
        form = xh_form()
        if not form.validates():
            return render.score(form=form)
        else:
            xh = form.d.xh
            score, jidi=get_score_jidi(xh)

            return render.result(table=score, jidian=jidi)

            # else:
            #    return "成绩查询源出错,请稍后再试!"

# 平均学分绩点计算说明页面


class help_gpa:

    @memorize(index_cache)
    def GET(self):
        return render.help_gpa()

# 评论页面, 使用多说评论

class comment:

    def GET(self):
        return render.comment()

# 赞助页面


class donate:

    def GET(self):
        return render.donate(sponsor=sponsor)

# 阿里妈妈认证


class ttest:

    def GET(self):
        return render.root()



def session_hook():
    """ share session with sub apps
    """
    web.ctx.session = session

def notfound():
    """404
    """
    return web.notfound(render.notfound())

def internalerror():
    """500
    """
    return web.internalerror(render.internalerror())

app.notfound = notfound
app.internalerror = internalerror
app.add_processor(web.loadhook(session_hook))

# for gunicorn
application = app.wsgifunc()
