<template>
  <view class="container">
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
          type="text"
          v-model="nickname"
          placeholder="昵称"
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
      <view class="input-group">
        <input
          type="password"
          v-model="confirmPassword"
          placeholder="确认密码"
          placeholder-style="color: #808080"
        />
      </view>
      
      <button class="register-btn" @tap="handleRegister">注册</button>
      <view class="login-link" @tap="goToLogin">
        <text>已有账号？立即登录</text>
      </view>
    </view>
  </view>
</template>

<script>
export default {
  data() {
    return {
      username: '',
      nickname: '',
      password: '',
      confirmPassword: ''
    }
  },
  methods: {
    handleRegister() {
      if (!this.username || !this.nickname || !this.password || !this.confirmPassword) {
        uni.showToast({
          title: '请填写完整信息',
          icon: 'none'
        });
        return;
      }
      
      if (this.password !== this.confirmPassword) {
        uni.showToast({
          title: '两次密码输入不一致',
          icon: 'none'
        });
        return;
      }
      
      // 模拟注册成功
      uni.showToast({
        title: '注册成功',
        icon: 'success',
        duration: 1500
      });
      
      // 延迟跳转到登录页
      setTimeout(() => {
        uni.navigateBack();
      }, 1500);
    },
    
    goToLogin() {
      uni.navigateBack();
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

.register-btn {
  background-color: #007AFF;
  color: #ffffff;
  border-radius: 12px;
  padding: 12px;
  font-size: 16px;
  margin-top: 30px;
  border: none;
}

.register-btn:active {
  opacity: 0.8;
}

.login-link {
  text-align: center;
  margin-top: 20px;
  color: #007AFF;
  font-size: 14px;
}
</style> 