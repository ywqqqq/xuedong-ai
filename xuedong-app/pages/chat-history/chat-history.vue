<template>
	<view class="container">
		<scroll-view class="chat-list" scroll-y 
			refresher-enabled 
			:refresher-triggered="isRefreshing"
			@refresherrefresh="onRefresh"
		>
			<view v-if="chatList.length === 0" class="empty-state">
				<text class="empty-text">暂无聊天记录</text>
			</view>
			<view 
				v-else
				class="chat-item" 
				v-for="(chat, index) in chatList" 
				:key="chat.session_id"
				@click="openChat(chat)"
			>
				<view class="chat-info">
					<text class="chat-title">{{ chat.preview }}</text>
					<text class="chat-time">{{ formatTime(chat.start_time) }}</text>
				</view>
				<text class="chat-preview">共 {{ chat.message_count }} 条对话</text>
			</view>
		</scroll-view>
	</view>
</template>

<script>
export default {
	data() {
		return {
			chatList: [],
			isRefreshing: false
		}
	},
	onLoad() {
		this.loadChatHistory();
	},
	methods: {
		// 加载聊天历史
		async loadChatHistory() {
			try {
				const response = await uni.request({
					url: 'http://10.65.1.110:8001/user/1/sessions',
					method: 'GET'
				});

				if (response.statusCode === 200 && response.data.sessions) {
					this.chatList = response.data.sessions;
				} else {
					throw new Error('获取聊天记录失败');
				}
			} catch (error) {
				console.error('获取聊天记录失败:', error);
				uni.showToast({
					title: '获取聊天记录失败',
					icon: 'none'
				});
			}
		},

		// 格式化时间
		formatTime(timeStr) {
			const date = new Date(timeStr);
			const now = new Date();
			const diff = now - date;
			
			// 处理无效日期
			if (isNaN(date.getTime())) {
				return timeStr;
			}
			
			if (diff < 24 * 60 * 60 * 1000) {
				// 当天显示时间
				return date.toTimeString().slice(0, 5);
			} else if (diff < 7 * 24 * 60 * 60 * 1000) {
				// 一周内显示星期
				const days = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
				return days[date.getDay()];
			} else {
				// 超过一周显示日期
				return `${date.getMonth() + 1}月${date.getDate()}日`;
			}
		},

		// 打开聊天
		openChat(chat) {
			uni.navigateTo({
				url: `/pages/index/index?sessionId=${chat.session_id}`,
				fail: (err) => {
					console.error('导航失败：', err);
					uni.showToast({
						title: '页面跳转失败',
						icon: 'none'
					});
				}
			});
		},

		// 下拉刷新
		async onRefresh() {
			this.isRefreshing = true;
			await this.loadChatHistory();
			this.isRefreshing = false;
		}
	}
}
</script>

<style>
.container {
	background-color: #1c1c1e;
	min-height: 100vh;
}

.chat-list {
	padding: 10px 16px;
	height: 100vh;
}

.chat-item {
	background-color: #2c2c2e;
	border-radius: 12px;
	padding: 16px;
	margin-bottom: 10px;
	transition: opacity 0.2s;
}

.chat-item:active {
	opacity: 0.7;
}

.chat-info {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-bottom: 8px;
}

.chat-title {
	color: #ffffff;
	font-size: 16px;
	flex: 1;
}

.chat-time {
	color: #808080;
	font-size: 14px;
	margin-left: 10px;
}

.chat-preview {
	color: #808080;
	font-size: 14px;
}

.empty-state {
	display: flex;
	justify-content: center;
	align-items: center;
	height: 200px;
}

.empty-text {
	color: #808080;
	font-size: 16px;
}
</style> 