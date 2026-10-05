from django.shortcuts import redirect, render
import random
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from .email_utils import send_otp_email,send_welcome_email
from django_ratelimit.decorators import ratelimit


from django.contrib.auth import authenticate, get_user_model, login, logout
User=get_user_model()
# Create your views here.

OTP_TIMEOUT = 600
OTP_MAX_ATTEMPTS = 5


#generate otp
def generate_otp():
    return str(random.randint(100000,999999))

def get_registration_cache_key(email):
    return f"registration:{email}"

def get_otp_cache_key(email):
    return f"otp:{email}"

def get_attempts_cache_key(email):
    return f"otp_attempts:{email}"



@ratelimit(key='ip',rate='5/h',method='POST',block=True)
def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method=='POST':
        first_name=request.POST.get('first_name','').strip()
        last_name=request.POST.get('last_name','').strip()
        email=request.POST.get('email','').strip().lower()
        phone=request.POST.get('phone','').strip()
        password=request.POST.get('password','')
        confirm_password=request.POST.get('confirm_password','')

        #validate the fields
        if not first_name:
            messages.error(request,"firstname required")
            return redirect('register')
        if not last_name:
            messages.error(request,"lastname required")
            return redirect('register')
        if not email:
            messages.error(request,"email required")
            return redirect('register')
        if not phone:
            messages.error(request,"phone number required")
            return redirect('register')
        if not password:
            messages.error(request,"password required")
            return redirect('register')
        if not confirm_password:
            messages.error(request,"confirm password required")
            return redirect('register')

        #password validation
        if len(password)<8:
            messages.warning(request,'password must be more then 8 digits')
            return redirect('register')
        if password!=confirm_password:
            messages.error(request,'password not matched')
            return redirect('register')

        #check user already exists or not
        if User.objects.filter(email=email).exists():
            messages.error(request,'User already exists')
            return redirect('login')

        #generate otp
        otp=generate_otp()

        #
        password_hash=make_password(password)
        registered_data={
            "email":email,
            "password":password_hash,
            "first_name":first_name,
            "last_name":last_name,
            "phone":phone
        }

        #store the data in catch
        cache.set(get_registration_cache_key(email),registered_data,timeout=OTP_TIMEOUT)
        cache.set(get_otp_cache_key(email),otp,timeout=OTP_TIMEOUT)
        cache.set(get_attempts_cache_key(email),0,timeout=OTP_TIMEOUT)

        #send email throug otp 
        try:
            send_otp_email(email,first_name,otp)
        except Exception:
            cache.delete(get_registration_cache_key(email))
            cache.delete(get_otp_cache_key(email))
            cache.delete(get_attempts_cache_key(email))
            messages.error(request,'unable to send otp try again')
            return redirect('register')
        request.session['verification_email']=email
        messages.success(request,'OTP sended succesfully to the registerd email')
        return render(request,'accounts/verify_otp.html',{'email':email})        
        
    return render(request,'accounts/register.html')




@ratelimit(
    key="ip",
    rate="10/10m",
    method="POST",
    block=True
)
@ratelimit(
    key="ip",
    rate="10/m",
    method="POST",
    block=True
)
@ratelimit(
    key="post:email",
    rate="5/m",
    method="POST",
    block=True
)
def verify_otp_view(request):
    email=request.session.get('verification_email')
    if not email:
        messages.error(request,'verification session expired.please register again')
        return redirect('register')
    if request.method=='POST':
        otp=request.POST.get('otp','')
        if not otp or len(otp)!=6:
            messages.warning(request,'please enter valid otp ')
            return redirect('verify_otp')
        #get otp from radis
        stored_otp=cache.get(get_otp_cache_key(email))
        if not stored_otp:
            messages.error(request,'otp expired please register again')
            return redirect('register')

        attempts=cache.get(get_attempts_cache_key(email),0)
        if attempts>=OTP_MAX_ATTEMPTS:
            messages.error(request,'Too many incorrect trys please try again')
            return redirect('register')

        if otp!=stored_otp:
            attempts+=1
            cache.set(get_attempts_cache_key(email),attempts,timeout=OTP_TIMEOUT)
            remaing_attempts=OTP_MAX_ATTEMPTS-attempts
            messages.error(request,f'only {remaing_attempts} left')
            return redirect('verify_otp')

        #get the user data
        registerd_data=cache.get(get_registration_cache_key(email))
        if not registerd_data:
            messages.warning(request,'verification session expire please register again')
            return redirect('register')

        #create user
        try:
            user=User.objects.create(
                first_name=registerd_data['first_name'],
                last_name=registerd_data['last_name'],
                email=registerd_data['email'],
                phone=registerd_data['phone'],
                password=registerd_data['password']
            )
        except Exception:
            messages.warning(request,'unable to create the user')
            return redirect('register')

        cache.delete(get_registration_cache_key(email))
        cache.delete(get_attempts_cache_key(email))
        cache.delete(get_otp_cache_key(email))

        request.session.pop('verification_email',None)
        try:
            send_welcome_email(user.email,user.first_name)
        except Exception:
            pass
        
        messages.success(request,'register succesfull')
        return redirect('login')
    return render(request,'accounts/verify_otp.html',{'email':email})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method=='POST':
        email=request.POST.get('email')
        password=request.POST.get('password')

        if not email or not password:
            messages.error(request,'email and password must be required')
            return redirect('login')

        if not User.objects.filter(email=email).exists():
            messages.error(request,'User not found')
            return redirect('register')
        user=authenticate(request,username=email,password=password)
        if user is None:
            messages.error(request,'Invalid username or password')
            return redirect('login')
        if user.status!='ACTIVE':
            messages.warning(request,'Your account is currently disabled please contact adminstration')
            return redirect('login')
        login(request,user)
        return redirect('home')
    
    return render(request,'accounts/login.html')

def logout_view(request):
    logout(request)
    messages.success(request,'logout succesfully')
    return redirect('login')
