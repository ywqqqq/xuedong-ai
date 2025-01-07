<template>
  <view class="container">
    <view class="logo-box">
      <image class="logo" src="/static/logo.png" mode="aspectFit"></image>
      <text class="title">AI-teacher</text>
    </view>
    
    <view class="form">
      <view class="input-group">
        <input 
          type="text"
          v-model="username"
          placeholder="用户名"
          placeholder-style="color: #808080"
        />
      </view>
      <view class="input-group">
        <input
          type="password"
          v-model="password"
          placeholder="密码"
          placeholder-style="color: #808080"
        />
      </view>
      
      <button class="login-btn" @tap="handleLogin">登录</button>
      <view class="register-link" @tap="goToRegister">
        <text>还没有账号？立即注册</text>
      </view>
    </view>
  </view>
</template>

<script>
export default {
  data() {
    return {
      username: '',
      password: ''
    }
  },
  methods: {
    handleLogin() {
      if (!this.username || !this.password) {
        uni.showToast({
          title: '请输入用户名和密码',
          icon: 'none'
        });
        return;
      }
      
      // 验证用户名和密码
      if (this.username === 'tty' && this.password === '123456') {
        // 保存用户信息
        uni.setStorageSync('userInfo', {
          user_id: 1,
          username: 'tty',
          nickname: '懵懂的小学生童天宇'
        });
        
        // 显示加载提示
        uni.showLoading({
          title: '登录中...',
          mask: true
        });
        
        // 直接跳转到首页，不需要弹出确认框
        uni.reLaunch({
          url: '/pages/index/index',
          success: () => {
            // 延迟执行以确保页面加载完成
            setTimeout(() => {
              // 发送开启新对话事件
              uni.$emit('startNewChat');
              uni.hideLoading();
            }, 500);
          },
          fail: (error) => {
            console.error('页面跳转失败:', error);
            uni.hideLoading();
            uni.showToast({
              title: '登录失败',
              icon: 'none'
            });
          }
        });
      } else {
        uni.showToast({
          title: '用户名或密码错误',
          icon: 'none'
        });
      }
    },
    
    goToRegister() {
      uni.navigateTo({
        url: '/pages/register/register'
      });
    }
  }
}
</script>

<style>
.container {
  padding: 40px 30px;
  background-color: #1c1c1e;
  min-height: 100vh;
}

.logo-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 60px;
}

.logo {
  width: 100px;
  height: 100px;
  margin-bottom: 20px;
}

.title {
  font-size: 24px;
  color: #ffffff;
  font-weight: bold;
}

.form {
  width: 100%;
}

.input-group {
  background-color: #2c2c2e;
  border-radius: 12px;
  padding: 12px 16px;
  margin-bottom: 20px;
}

.input-group input {
  color: #ffffff;
  font-size: 16px;
  width: 100%;
}

.login-btn {
  background-color: #007AFF;
  color: #ffffff;
  border-radius: 12px;
  padding: 12px;
  font-size: 16px;
  margin-top: 30px;
  border: none;
}

.login-btn:active {
  opacity: 0.8;
}

.register-link {
  text-align: center;
  margin-top: 20px;
  color: #007AFF;
  font-size: 14px;
}
</style> 