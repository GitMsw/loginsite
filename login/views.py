from django.shortcuts import render, redirect
from . import models
from . import forms
from captcha.models import CaptchaStore
from captcha.helpers import captcha_image_url
from django.http import JsonResponse
from .models import hash_code
from django.core.mail import send_mail
from django.conf import settings
import datetime

def send_email(email, code):
    from django.core.mail import EmailMultiAlternatives
    subject = f'来自{settings.BLOG_NAME}的注册确认邮件'
    print(subject)
    text_content = '''感谢注册，这里是msw的博客和教程站点，专注于python，如果你看到这条消息，说明你的邮箱服务器不支持HTML链接功能，请联系管理员'''
    html_content = '''
                    <p>感谢注册<a href="http://{}/confirm/?code={}" target=blank>www.mengpy.com</a>，\
                    这里是刘江的博客和教程站点，专注于Python、Django和机器学习技术的分享！</p>
                    <p>请点击站点链接完成注册确认！</p>
                    <p>此链接有效期为{}天！</p>
                    '''.format('127.0.0.1:8000', code, settings.CONFIRM_DAYS)
    msg = EmailMultiAlternatives(subject, text_content, settings.EMAIL_HOST_USER, [email])
    msg.attach_alternative(html_content, 'text/html')
    try:
        msg.send()
        return True
    except:
        return False

def make_confirm_string(user):
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    code = hash_code(user.name, now)
    models.ConfirmString.objects.create(code=code, user=user)
    return code


# Create your views here.
def index(request):
    if not request.session.get('is_login', None):  # 不允许重复登录
        message = '用户未登录,不能发送邮件'
        return render(request, 'login/index.html', locals())
    elif request.method == 'POST':
        email_text = request.POST.get('email')
        if email_text:
            email_title = '邮件标题 test'
            email_body = email_text
            user = models.User.objects.get(name=request.session.get('user_name', None))
            email = user.email  # 对方的邮箱
            send_status = send_mail(email_title, email_body, settings.EMAIL_FROM, [email])
            if send_status:
                message = '邮件已经发送成功，注意查看'
                return render(request, 'login/index.html', locals())
            else:
                message = '邮件发送失败'
                return render(request, 'login/index.html', locals())
    return render(request, 'login/index.html', locals())


def login(request):
    '''
    对于非POST方法发送数据时，比如GET方法请求页面，返回空的表单，让用户可以填入数据；
    对于POST方法，接收表单数据，并验证；
    使用表单类自带的is_valid()方法一步完成数据验证工作；
    验证成功后可以从表单对象的cleaned_data数据字典中获取表单的具体值；
    如果验证不通过，则返回一个包含先前数据的表单给前端页面，方便用户修改。也就是说，它会帮你保留先前填写的数据内容，而不是返回一个空表！
    :param request:
    :return:
    '''
    if request.session.get('is_login', None):  # 不允许重复登录
        return redirect('/index/')

    if request.is_ajax():  # 请求ajax则返回新的image_url和key
        result = dict()
        result['key'] = CaptchaStore.generate_key()
        result['image_url'] = captcha_image_url(result['key'])
        return JsonResponse(result)  # #如果这样返回，两边都不需要进行json的序列化与反序列化，ajax接受的直接是一个对象

    if request.method == 'POST':
        login_form = forms.UserForm(request.POST)
        message = '情检查填写的内容'
        if login_form.is_valid():
            username = login_form.cleaned_data.get('username')
            password = login_form.cleaned_data.get('password')
            try:
                user = models.User.objects.get(name=username)
            except:
                message = '用户不存在'
                return render(request, 'login/login.html', locals())

            if not user.has_confirmed:
                message = '该用户还未经过邮件确认！'
                return render(request, 'login/login.html', locals())

            if user.password == hash_code(password):
                request.session['is_login'] = True
                request.session['user_id'] = user.id
                request.session['user_name'] = user.name
                print(username, password)
                return redirect('/index/')
            else:
                message = '密码不正常'
                print('user.password = ',user.password )
                print('hash_code(password)=',hash_code(password))
                return render(request, 'login/login.html', locals())
        else:
            return render(request, 'login/login.html', locals())
    login_form = forms.UserForm()
    return render(request, 'login/login.html', locals())


def register(request):
    if request.session.get('is_login', None):
        return redirect('/index/')

    if request.is_ajax():  # 请求ajax则返回新的image_url和key
        result = dict()
        result['key'] = CaptchaStore.generate_key()
        result['image_url'] = captcha_image_url(result['key'])
        return JsonResponse(result)  # #如果这样返回，两边都不需要进行json的序列化与反序列化，ajax接受的直接是一个对象

    if request.method == 'POST':
        register_form = forms.RegisterForm(request.POST)
        message = '请检查填写的内容'
        if register_form.is_valid():
            username = register_form.cleaned_data.get('username')
            password1 = register_form.cleaned_data.get('password1')
            password2 = register_form.cleaned_data.get('password2')
            email = register_form.cleaned_data.get('email')
            sex = register_form.cleaned_data.get('sex')
            if password1 != password2:
                return render(request, 'login/register.html', locals())
            else:
                same_name_user = models.User.objects.filter(name=username)
                if same_name_user:
                    message = '用户已经存在'
                    return render(request, 'login/register.html', locals())
                same_name_email = models.User.objects.filter(email=email)
                if same_name_email:
                    message = '邮箱已经存在'
                    return render(request, 'login/register.html', locals())
                new_user = models.User()
                new_user.name = username
                new_user.password = password1
                print('register_password = ', hash_code(password1))
                new_user.email = email
                new_user.sex = sex
                new_user.save()

                code = make_confirm_string(new_user)
                res = send_email(email, code)
                if res:
                    message = '请前往邮箱进行确认'
                    return redirect('/login/')
                else:
                    user = models.User.objects.get(name=username)
                    user.delete()
                    message = '邮箱不可达，请确认输入是否正确'
                    return render(request, 'login/register.html', locals())
        else:
            return render(request, 'login/register.html', locals())
    return render(request, 'login/register.html', locals())


def logout(request):
    if not request.session.get('is_login', None):
        return redirect('/login/')
    request.session.flush()
    return redirect('/login/')

def user_confirm(request):
    code = request.GET.get('code', None)
    print('code=',code)
    message = ''
    try:
        confirm = models.ConfirmString.objects.get(code=code)
    except:
        message = '无效请求！'
        return render(request, 'login/confirm.html', locals())

    c_time = confirm.c_time
    now = datetime.datetime.now()
    if now > c_time + datetime.timedelta(settings.CONFIRM_DAYS):
        confirm.user.delete()
        message = '您的邮箱已经过期，请重新注册！'
        return render(request, 'login/confirm.html', locals())
    else:
        confirm.user.has_confirmed = True
        confirm.user.save()
        confirm.delete()  # 只是删除注册码
        message = '感谢确认，请使用账户登录！'
        return render(request, 'login/confirm.html', locals())