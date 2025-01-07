<script>
	export default {
		onLaunch: function() {
			console.log('App Launch')
			// 检查登录状态
			const userInfo = uni.getStorageSync('userInfo');
			if (!userInfo) {
				uni.reLaunch({
					url: '/pages/login/login'
				});
			}
		},
		onShow: function() {
			console.log('App Show')
		},
		onHide: function() {
			console.log('App Hide')
		}
	}
</script>

<style>
	/*每个页面公共css */
</style>
