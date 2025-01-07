<template>
	<view class="container" :style="{ paddingTop: statusBarHeight + 'px' }">
		<!-- 顶部状态栏占位 -->
		<view class="status-bar" :style="{ height: statusBarHeight + 'px' }"></view>
		
		<!-- 侧边栏 -->
		<view class="sidebar" :class="{ 'sidebar-show': showSidebar }">
			<view class="sidebar-header">
				<image class="user-avatar" src="/static/logo.png"></image>
				<text class="user-name">懵懂小学生tty</text>
			</view>
			<view class="sidebar-content">
				<view class="sidebar-item" @click.stop="goToChatHistory">
					<text class="sidebar-icon">📝</text>
					<text>聊天记录</text>
				</view>
				<view class="sidebar-item" @click.stop="goToFuzzyKnowledge">
					<text class="sidebar-icon">📚</text>
					<text>模糊知识</text>
				</view>
				<view class="sidebar-item" @click.stop="goToDailyQuestion">
					<text class="sidebar-icon">📅</text>
					<text>每日一题</text>
				</view>
				<view class="sidebar-item">
					<text class="sidebar-icon">⚙️</text>
					<text>设置</text>
				</view>

				<view class="sidebar-item" @click.stop="handleLogout">
					<text class="sidebar-icon">🚪</text>
					<text>退出登录</text>
				</view>
			</view>
		</view>

		<!-- 遮罩层 -->
		<view class="mask" v-if="showSidebar" @click="toggleSidebar"></view>

		<!-- 顶部状态栏 -->
		<view class="header">
			<view class="left" @click="toggleSidebar">
				<text class="menu-icon">☰</text>
			</view>
			<view class="center">
				<text class="title">AI-teacher</text>
			</view>
			<view class="right">
				<text class="icon">🔇</text>
				<text class="icon" @click="startNewChat(false)">🔄</text>
			</view>
		</view>

		<!-- 聊天内容区域 -->
		<scroll-view 
			class="chat-container" 
			scroll-y 
			:scroll-top="scrollTop"
			:scroll-with-animation="true"
			@scroll="onScroll"
			@scrolltolower="onScrollToLower"
			refresher-enabled
			:refresher-triggered="isRefreshing"
			@refresherrefresh="onRefresh"
			ref="chatScroll"
		>
			<!-- AI头像和欢迎消息 -->
			<view class="message ai-message" v-if="chatMessages.length === 0">
				<image class="avatar" src="/static/ai-avatar.png"></image>
				<view class="message-content">
					<text>你好，我是AI老师。</text>
				</view>
			</view>

			<!-- 聊天记录 -->
			<view v-for="(msg, index) in chatMessages" :key="index" 
				:class="['message', msg.type === 'user' ? 'user-message' : 'ai-message']">
				<image v-if="msg.type === 'ai'" class="avatar" src="/static/ai-avatar.png"></image>
				<view class="message-content" 
					:class="{'voice-message': msg.messageType === 'voice'}"
					@click="msg.messageType === 'voice' && playVoiceMessage(msg)">
					<!-- 图片消息 -->
					<image 
						v-if="msg.image" 
						:src="msg.image" 
						class="message-image" 
						mode="widthFix"
						@tap="previewImage(msg.image)"
					/>
					<!-- AI回复使用markdown渲染 -->
					<view v-if="msg.type === 'ai' && !msg.messageType" class="ai-response">
						<rich-text 
							:nodes="formatMarkdown(msg.content)"
							class="markdown-content"
						/>
						<view class="ai-voice-control" @tap.stop="playAIResponse(msg)">
							<text class="voice-icon">{{ msg.isPlaying ? '⏸️' : '🔊' }}</text>
							<text class="voice-text">{{ msg.isPlaying ? '暂停' : '播放语音' }}</text>
						</view>
						<view v-if="msg.followUpSuggestions && msg.followUpSuggestions.length" class="follow-up-suggestions">
							<text class="suggestions-title">建议继续问：</text>
							<view 
								v-for="(suggestion, index) in msg.followUpSuggestions" 
								:key="index"
								class="suggestion-item"
								@tap="askSuggestion(suggestion)"
							>
								<text class="suggestion-text">{{ suggestion }}</text>
							</view>
						</view>
					</view>
					<!-- 用户消息仍然使用普通文本 -->
					<text v-else-if="!msg.messageType">{{msg.content}}</text>
					<!-- 语音消息 -->
					<view v-else-if="msg.messageType === 'voice'" class="voice-content">
						<text class="voice-icon">🔊</text>
						<text class="voice-duration">{{msg.duration}}″</text>
						<text class="playing-indicator" v-if="currentPlayingAudio === msg.content">▶</text>
					</view>
				</view>
				<image v-if="msg.type === 'user'" class="avatar" src="/static/user-avatar.png"></image>
			</view>

			<!-- 显示正在输入状态 -->
			<view v-if="isAiTyping" class="message ai-message">
				<image class="avatar" src="/static/ai-avatar.png"></image>
				<view class="message-content typing">
					<text>正在输入...</text>
				</view>
			</view>

			<!-- 图片预览区域 -->
			<view class="preview-area" v-if="tempImage">
				<view class="preview-wrapper">
					<image :src="tempImage" class="preview-image" mode="aspectFill"/>
					<view class="preview-close" @tap="clearImage">×</view>
				</view>
			</view>

			<!-- 在语音输入区域添加试听界面 -->
			<view v-if="isPreviewingVoice" class="voice-preview">
				<view class="preview-controls">
					<button 
						class="preview-btn" 
						:class="{ 'playing': isPreviewPlaying }"
						@tap="playPreview"
					>
						{{ isPreviewPlaying ? '停止' : '试听' }}
					</button>
					<button class="submit-btn" @tap="confirmVoiceSubmit">确认发送</button>
					<button class="cancel-btn" @tap="cancelVoiceSubmit">取消</button>
				</view>
			</view>
		</scroll-view>

		<!-- 底部工具栏 -->
		<view class="footer">
			<!-- 正常工具栏 -->
			<view class="tool-bar" v-if="!isRecording && !showVoiceBtn">
				<view class="tool-item" @tap="takePhoto">
					<!-- <image class="tool-icon" src="/static/camera.png"></image> -->
					<text>拍照解题</text>
				</view>
				<view class="tool-item">
					<!-- <image class="tool-icon" src="/static/phone.png"></image> -->
					<text>打电话</text>
				</view>
				<view class="tool-item">
					<!-- <image class="tool-icon" src="/static/translate.png"></image> -->
					<text>针对出题</text>
				</view>
				<view class="tool-item">
					<!-- <image class="tool-icon" src="/static/write.png"></image> -->
					<text>写作</text>
				</view>
			</view>
			
			<!-- 输入区域 -->
			<view v-if="!showVoiceBtn" class="input-area">
				<text class="mic-icon" v-if="!inputText && isRecordingSupported" @click="showVoiceInput">🎤</text>
				<input 
					type="text" 
					v-model="inputText"
					placeholder="有什么问题尽管问我" 
					class="chat-input"
					@confirm="handleConfirm"
				/>
				<template v-if="!inputText">
					<text class="plus-icon" @tap="showImageOptions">+</text>
					<text class="send-icon">📞</text>
				</template>
				<text v-else class="send-btn" @click="sendMessage">发送</text>
			</view>

			<!-- 语音输入按钮 -->
			<view v-else class="voice-input-area" 
				@touchstart="startRecording" 
				@touchend="stopRecording"
				@touchcancel="cancelRecording">
				<text class="voice-btn" :class="{ 'recording': isRecording }">
					{{ isRecording ? '松开结束' : '按住说话' }}
				</text>
				<text class="cancel-voice" @click="cancelVoiceInput">取消</text>
			</view>
		</view>
	</view>
</template>

<script>
import { marked } from 'marked';
import katex from 'katex';
import 'katex/dist/katex.min.css';

// 添加音频管理器
const audioManager = uni.createInnerAudioContext();
// 添加平台判断
const recorderManager = uni.getRecorderManager ? uni.getRecorderManager() : null;

export default {
	data() {
		return {
			showSidebar: false,
			inputText: '',
			showVoiceBtn: false,
			isRecording: false,
				voiceFile: null,
				chatMessages: [], // 聊天记录
				isAiTyping: false, // AI 输入状态
				scrollTop: 0, // 滚动位置
				currentPlayingAudio: null, // 当前正在播放的音频消息ID
				isPlaying: false, // 音频播放状态
				audioManager: null, // 添加音频管理器引用
				tempImage: '', // 临时存储拍摄的图片路径
				sessionId: null, // 会话ID
				isRefreshing: false,
				domain: 'https://example.com', // 设置域名，用于处理相对链接
				currentPlayingMsg: null, // 当前正在播放的消息
				isRecordingSupported: !!uni.getRecorderManager, // 添加录音支持状态
				statusBarHeight: 0,
				_recordStartTime: 0, // 记录开始录音的时间
				tempVoiceFile: null, // 临时存储录音文件
				isPreviewingVoice: false, // 是否在试听
				isPreviewPlaying: false, // 试听播放状态
		}
	},
	methods: {
		toggleSidebar() {
			this.showSidebar = !this.showSidebar;
		},
		// 显示语音输入界面
		showVoiceInput() {
			if (!this.isRecordingSupported) {
				uni.showToast({
					title: '当前平台不支持录音功能',
					icon: 'none'
				});
				return;
			}
			this.showVoiceBtn = true;
		},
		// 取消语音输入
		cancelVoiceInput() {
			this.showVoiceBtn = false;
			this.isRecording = false;
		},
		// 开始录音
		startRecording() {
			if (!this.isRecordingSupported) {
				uni.showToast({
					title: '当前平台不支持录音功能',
					icon: 'none'
				});
				return;
			}
			
			console.log('开始录音');
			
			this.isRecording = true;
			this._recordStartTime = Date.now(); // 记录开始时间
			
			recorderManager.start({
				format: 'wav',
				duration: 60000,
				sampleRate: 16000,
				numberOfChannels: 1,
				encodeBitRate: 48000,
				frameSize: 4,
				audioSource: 'auto'
			});

			// 添加录音开始事件监听
			recorderManager.onStart(() => {
				console.log('录音开始');
				// 添加震动反馈
				uni.vibrateShort({
					success: function () {
						console.log('震动成功');
					}
				});
			});
		},
		// 停止录音
		async stopRecording() {
			if (!this.isRecordingSupported || !this.isRecording) return;
			
			const recordingDuration = Date.now() - this._recordStartTime;
			
			// 检查录音时长是否太短（小于1秒）
			if (recordingDuration < 1000) {
				uni.showToast({
					title: '录音时间太短',
					icon: 'none'
				});
				this.cancelRecording();
				return;
			}
			
			this.isRecording = false;
			recorderManager.stop();
		},
		// 取消录音
		cancelRecording() {
			if (!this.isRecordingSupported) return;
			this.isRecording = false;
			recorderManager.stop();
			this.showVoiceBtn = false; // 隐藏语音输入界面
		},
		// 调用API发送消息
		async callChatAPI(query, imageUrl = null) {
			try {
				console.log('Calling API with:', { query, imageUrl }); // 添加日志
				
				const response = await uni.request({
					url: 'http://10.65.1.110:8001/chat',
					method: 'POST',
					header: {
						'Content-Type': 'application/x-www-form-urlencoded',
						'Accept': '*/*'
					},
					data: {
						text: query,
						user_id: 1,
						session_id: this.sessionId || '',
						...(imageUrl ? { image_url: imageUrl } : {})
					}
				});
				
				console.log('API Response:', response); // 添加日志
				
				if (response.statusCode === 200) {
					if (response.data.session_id) {
						this.sessionId = response.data.session_id;
					}
					return response.data;
				} else {
					throw new Error(`API请求失败: ${response.statusCode}`);
				}
			} catch (error) {
				console.error('API调用错误：', error);
				throw error;
			}
		},
		// 添加确认输入的处理方法
		handleConfirm(e) {
			// 从事件对象中获取输入值
			const value = e.detail.value || this.inputText;
			if (value) {
				this.sendMessage(value);
			}
		},
		// 修改发送消息方法
		async sendMessage(input) {
			try {
				console.log('Input type:', typeof input);
				console.log('Input value:', input);
				console.log('Input detail:', input.detail);
				
				// 如果有图片，使用图片对话功能
				if (this.tempImage) {
					await this.sendImageMessage();
					return;
				}
				
				// 获取消息内容
				let messageContent;
				if (typeof input === 'object') {
					messageContent = input.detail?.value || this.inputText || '';
				} else {
					messageContent = String(input || this.inputText || '');
				}
				
				// 确保消息内容不为空
				if (!messageContent.trim()) return;
				
				// 添加用户消息
				const userMessage = {
					type: 'user',
					content: messageContent.trim(),
					time: Date.now()
				};
				
				this.chatMessages.push(userMessage);
				this.inputText = '';
				
				// 显示 AI 正在输入状态
				this.isAiTyping = true;
				
				// 检查是否匹配"xxx没有理解"模式
				const notUnderstandPattern = /^(.+?)没有理解/;
				const match = messageContent.match(notUnderstandPattern);

				if (match) {
					// 提取搜索内容（匹配的第一个捕获组）
					const searchContent = match[1].trim();
					
					if (searchContent) {
						// 模拟查找历史对话（这里简单返回第二条 AI 消息）
						let matchedMessage = null;
						let matchedIndex = 0;
						
						for (let i = 0; i < this.chatMessages.length; i++) {
							if (this.chatMessages[i].type === 'ai') {
								matchedIndex++;
								if (matchedIndex === 2) { // 获取第二条 AI 消息
									matchedMessage = this.chatMessages[i];
									break;
								}
							}
						}
						
						if (matchedMessage) {
							const aiMessage = {
								type: 'ai',
								content: `检索到您的问题"${searchContent}"与第${matchedIndex}次历史问题有关，已为您匹配这个回答：\n\n${matchedMessage.content}`,
								time: Date.now(),
								isPlaying: false
							};
							
							setTimeout(() => {
								this.chatMessages.push(aiMessage);
								this.isAiTyping = false;
								
								this.$nextTick(() => {
									this.scrollToBottom();
								});
							}, 1000);
							
							return;
						}
					}
				}
				
				// 调用 API 获取回复
				const response = await this.callChatAPI(messageContent);
				
				if (response) {
					const aiMessage = {
						type: 'ai',
						content: response.response || response,
						followUpSuggestions: response.follow_up_suggestions || [],
						time: Date.now(),
						isPlaying: false
					};
					
					this.chatMessages.push(aiMessage);
					this.isAiTyping = false; // 确保在添加消息后立即关闭输入状态
					
					// 保存到本地存储
					uni.setStorageSync('chatHistory', this.chatMessages);
					
					// 滚动到底部
					this.$nextTick(() => {
						this.scrollToBottom();
					});
				}
			} catch (error) {
				console.error('发送消息失败:', error);
				uni.showToast({
					title: '发送失败',
					icon: 'none'
				});
				this.isAiTyping = false; // 确保在错误时也关闭输入状态
			}
		},
		
		// 修改图片对话功能
		async sendImageMessage() {
			try {
				// 准备发送的消息数据
				const messageData = {
					content: this.inputText || '图片消息',
					image: this.tempImage,
					timestamp: Date.now()
				};
				
				// 添加到消息列表，包含图片
				this.chatMessages.push({
					type: 'user',
					content: messageData.content,
					image: messageData.image,
					time: messageData.timestamp
				});
				
				// 清空输入和临时图片变量
				this.inputText = '';
				this.tempImage = '';
				
				// 显示 AI 正在输入状态
				this.isAiTyping = true;
				
				// 显示上传提示
				uni.showLoading({
					title: '正在上传图片...',
					mask: true
				});
				
				// 1. 先上传图片
				const uploadResult = await this.uploadImage(messageData.image);
				
				if (!uploadResult || !uploadResult.url) {
					throw new Error('图片上传失败：未获取到URL');
				}
				
				// 2. 调用对话接口
				uni.showLoading({
					title: '正在处理...',
					mask: true
				});
				
				const response = await this.callChatAPI(messageData.content, uploadResult.url);
				
				// 确保在处理完成后关闭 AI 输入状态
				this.isAiTyping = false;
				uni.hideLoading();
				
				if (response) {
					// 添加 AI 回复消息
					this.chatMessages.push({
						type: 'ai',
						content: response.response || response, // 根据实际返回格式调整
						followUpSuggestions: response.follow_up_suggestions || [],
						time: Date.now()
					});
					
					// 滚动到底部
					this.$nextTick(() => {
						this.scrollToBottom();
					});
				}
			} catch (error) {
				console.error('图片消息发送失败:', error);
				this.isAiTyping = false; // 确保错误时也关闭输入状态
				uni.hideLoading();
				uni.showToast({
					title: error.message || '发送失败',
					icon: 'none',
					duration: 2000
				});
			}
		},
		
		// 上传图片方法
		async uploadImage(filePath) {
			return new Promise((resolve, reject) => {
				const uploadTask = uni.uploadFile({
					url: 'http://10.65.1.110:8002/uploadfile',
					filePath: filePath,
					name: 'file',
					formData: {},
					header: {
						'Accept': '*/*'
					},
					success: (res) => {
						console.log('Upload response:', res);
						try {
							if (typeof res.data === 'string') {
								const result = JSON.parse(res.data);
								resolve(result);
							} else {
								resolve(res.data);
							}
						} catch (e) {
							console.error('Parse response failed:', e, res.data);
							reject(new Error('解析响应数据失败'));
						}
					},
					fail: (err) => {
						console.error('Upload error:', err);
						reject(err);
					}
				});

				// 监听上传进度
				uploadTask.onProgressUpdate((res) => {
					console.log('上传进度：', res.progress);
					if (res.progress < 100) {
						uni.showLoading({
							title: `上传中 ${res.progress}%`,
							mask: true
						});
					} else {
						uni.hideLoading();
					}
				});
			});
		},
		
		// 滚动到底部
		scrollToBottom() {
			setTimeout(() => {
				const query = uni.createSelectorQuery().in(this);
				query.select('.chat-container').boundingClientRect(data => {
					if (data) {
						const chatContainer = document.querySelector('.chat-container');
						if (chatContainer) {
							chatContainer.scrollTop = chatContainer.scrollHeight;
						}
					}
				}).exec();
			}, 100);
		},
		
		// 监听滚动到底部事件
		onScrollToLower() {
			console.log('滚动到底部');
		},
		
		goToChatHistory() {
			this.showSidebar = false; // 关闭侧边栏
			// 添加延时确保侧边栏关闭动画完成后再跳转
			setTimeout(() => {
				uni.navigateTo({
					url: '/pages/chat-history/chat-history',
					fail: (err) => {
						console.error('导航失败：', err);
						uni.showToast({
							title: '页面跳转失败',
							icon: 'none'
						});
					}
				});
			}, 300);
		},
		// 处理录音完成
		async handleVoiceRecord(tempFilePath) {
			try {
				// 显示加载提示
				uni.showLoading({
					title: '正在识别...',
					mask: true
				});

				console.log('开始处理语音文件:', tempFilePath);

				// 1. 直接上传录音文件到语音识别接口
				const response = await uni.uploadFile({
					url: 'http://10.65.1.110:8002/api/asr',
					filePath: tempFilePath,
					name: 'file',
					formData: {},
					header: {
						'Accept': '*/*'
					}
				});

				console.log('语音识别响应:', response);

				// 2. 处理响应
				if (response.statusCode === 200) {
					try {
						console.log('原始响应数据:', response.data);
						
						// 尝试解析响应数据
						let result;
						if (typeof response.data === 'string') {
							result = JSON.parse(response.data);
						} else {
							result = response.data;
						}
						
						console.log('解析后的数据:', result);

						// 检查响应格式
						if (result.success) {
							if (!result.text || result.text.trim() === '') {
								// 处理空文本的情况
								uni.showToast({
									title: '未能识别到语音内容',
									icon: 'none',
									duration: 2000
								});
								return;
							}
							
							console.log('识别到的文本:', result.text);
							// 3. 将转换后的文本设置到输入框
							this.inputText = result.text;
							
							// 4. 自动发送消息
							await this.sendMessage(result.text);
						} else {
							console.error('语音识别失败:', result);
							throw new Error('语音识别失败');
						}
					} catch (e) {
						console.error('解析响应数据失败:', e);
						console.error('原始响应数据:', response.data);
						throw new Error('解析语音识别结果失败');
					}
				} else {
					console.error('请求失败:', response.statusCode, response.data);
					throw new Error(`语音识别请求失败: ${response.statusCode}`);
				}

			} catch (error) {
				console.error('语音处理失败:', error);
				uni.showToast({
					title: error.message || '语音识别失败',
					icon: 'none',
					duration: 2000
				});
			} finally {
				uni.hideLoading();
				this.showVoiceBtn = false;
			}
		},
		// 播放语音消息
		playVoiceMessage(message) {
			if (!message.content) return;
			
			// 如果正在播放同一条消息，则停止播放
			if (this.currentPlayingAudio === message.content) {
				audioManager.stop();
				this.currentPlayingAudio = null;
				return;
			}
			
			// 如果正在播放其他消息，先停止
			if (this.currentPlayingAudio) {
				audioManager.stop();
			}
			
			// 设置音频源并播放
			audioManager.src = message.content;
			audioManager.play();
			this.currentPlayingAudio = message.content;
			
			// 监听播放结束
			audioManager.onEnded(() => {
				this.currentPlayingAudio = null;
			});
			
			// 监听播放错误
			audioManager.onError((res) => {
				console.error('语音播放失败:', res);
				this.currentPlayingAudio = null;
				uni.showToast({
					title: '播放失败',
					icon: 'none'
				});
			});
		},
		// 拍照功能
		takePhoto() {
			uni.chooseImage({
				count: 1,
				sourceType: ['camera'],
				sizeType: ['compressed'],
				success: (res) => {
					this.tempImage = res.tempFilePaths[0];
					
					// 只在图片过大时提示
					uni.getFileInfo({
						filePath: res.tempFilePaths[0],
						success: (res) => {
							if (res.size > 1024 * 1024) {
								uni.showToast({
									title: '图片过大，建议压缩',
									icon: 'none'
								});
							}
						}
					});
				}
			});
		},
		// 清除图片
		clearImage() {
			this.tempImage = '';
		},
		// 添加新的方法来处理滚动
		onScroll(e) {
			// 可以在这里添加下拉加载更多历史消息的逻辑
			const scrollTop = e.detail.scrollTop;
			if (scrollTop === 0) {
				// 触发加载更多历史消息
				this.loadMoreHistory();
			}
		},
		// 添加加载更多历史消息的方法
		loadMoreHistory() {
			// 这里可以实现加载更多历史消息的逻辑
			console.log('Loading more history...');
		},
		// 处理下拉刷新
		async onRefresh() {
			this.isRefreshing = true;
			try {
				await this.loadMoreHistory();
			} finally {
				this.isRefreshing = false;
			}
		},
		// 添加图片预览方法
		previewImage(url) {
			uni.previewImage({
				urls: [url],
				current: url
			});
		},
		// 格式化 Markdown 内容
		formatMarkdown(content) {
			if (!content) return '';
			
			try {
				// 先处理数学公式
				content = content.replace(/\$\$(.*?)\$\$/g, (match, formula) => {
					try {
						return katex.renderToString(formula, {
							displayMode: true,
							throwOnError: false
						});
					} catch (e) {
						console.warn('Math formula rendering failed:', e);
						return match;
					}
				}).replace(/\$(.*?)\$/g, (match, formula) => {
					try {
						return katex.renderToString(formula, {
							displayMode: false,
							throwOnError: false
						});
					} catch (e) {
						console.warn('Math formula rendering failed:', e);
						return match;
					}
				});

				// 配置 marked 选项
				const renderer = new marked.Renderer();
				
				marked.setOptions({
					renderer: renderer,
					breaks: true,
					gfm: true,
					headerIds: false,
					mangle: false,
					headerPrefix: '',
				});
				
				// 将 Markdown 转换为 HTML
				let html = marked.parse(content, { renderer });
				
				// 处理代码高亮和表格样式
				html = html
					.replace(/<pre><code>/g, '<pre><code class="code-block">')
					.replace(/<table>/g, '<table class="md-table">');
					
				return html;
			} catch (error) {
				console.warn('Markdown parsing warning:', error);
				return content
					.replace(/\n/g, '<br>')
					.replace(/\t/g, '&nbsp;&nbsp;&nbsp;&nbsp;');
			}
		},
		
		// 处理链接点击
		onLinkTap(e) {
			// 处理链接点击事件
			uni.showModal({
				content: e.href,
				showCancel: false
			});
		},
		// 播放 AI 回复的语音
		async playAIResponse(msg) {
			try {
				// 如果正在播放，则停止
				if (msg.isPlaying) {
					audioManager.stop();
					msg.isPlaying = false;
					this.currentPlayingMsg = null;
					return;
				}

				// 如果有其他消息正在播放，先停止
				if (this.currentPlayingMsg) {
					this.currentPlayingMsg.isPlaying = false;
					audioManager.stop();
				}

				// 显示加载提示
				uni.showLoading({
					title: '准备播放...'
				});

				// 调用文字转语音 API
				const response = await uni.request({
                    url: 'http://10.65.1.110:8002/api/tts',  // 替换为实际的 API 地址
                    method: 'POST',
                    data: {
                        text: msg.content
                    }
                });


                if (response.statusCode === 200 && response.data.file_url) {
                    // 播放语音
                    // audioManager.src = response.data.file_url;
                    audioManager.src = response.data.file_url;
                    audioManager.play();
                    
                    // 更新状态
                    msg.isPlaying = true;
                    this.currentPlayingMsg = msg;
				}else{
					console.error('语音转换失败:', response);
					uni.showToast({
						title: '语音转换失败',
						icon: 'none'
					});
				}

				// 监听播放结束
				audioManager.onEnded(() => {
					msg.isPlaying = false;
					this.currentPlayingMsg = null;
				});

				// 监听播放错误
				audioManager.onError((res) => {
					console.error('Audio playback error:', res);
					msg.isPlaying = false;
					this.currentPlayingMsg = null;
					uni.showToast({
						title: '音频播放失败',
						icon: 'none'
					});
				});

				// 监听加载完成
				audioManager.onCanplay(() => {
					uni.hideLoading();
				});

			} catch (error) {
				console.error('音频播放错误：', error);
				uni.showToast({
					title: '音频播放失败',
					icon: 'none'
				});
				msg.isPlaying = false;
				this.currentPlayingMsg = null;
			} finally {
				uni.hideLoading();
			}
		},
		// 修改建议问题处理方法
		askSuggestion(suggestion) {
			if (!suggestion) return;
			console.log('选择了建议问题:', suggestion); // 添加日志
			this.sendMessage(suggestion);
		},
		// 获取状态栏高度
		getStatusBarHeight() {
			// #ifdef APP-PLUS || MP
			this.statusBarHeight = uni.getSystemInfoSync().statusBarHeight || 0;
			// #endif
			
			// #ifdef H5
			this.statusBarHeight = 0;
			// #endif
		},
		// 添加显示图片选项的方法
		showImageOptions() {
			uni.showActionSheet({
				itemList: ['拍照', '从相册选择'],
				success: (res) => {
					switch (res.tapIndex) {
						case 0: // 拍照
							this.takePhoto();
							break;
						case 1: // 从相册选择
							this.chooseFromAlbum();
							break;
					}
				}
			});
		},

		// 修改从相册选择图片的方法
		chooseFromAlbum() {
			uni.chooseImage({
				count: 1,
				sourceType: ['album'],
				sizeType: ['compressed'],
				success: (res) => {
					this.tempImage = res.tempFilePaths[0];
					
					// 只在图片过大时提示
					uni.getFileInfo({
						filePath: res.tempFilePaths[0],
						success: (res) => {
							if (res.size > 1024 * 1024) {
								uni.showToast({
									title: '图片过大，建议压缩',
									icon: 'none'
								});
							}
						}
					});
				}
			});
		},

		// 修改加载会话消息的方法
		async loadSessionMessages(sessionId) {
			uni.showLoading({
				title: '加载消息...',
				mask: true
			});
			
			try {
				const response = await uni.request({
					url: `http://10.65.1.110:8001/chat/${sessionId}/messages`,
						method: 'GET'
				});

				if (response.statusCode === 200 && response.data.messages) {
					// 处理消息数据
					this.chatMessages = response.data.messages.map(msg => {
						// 基础消息结构
						const baseMessage = {
							type: msg.role === 'user' ? 'user' : 'ai',
							time: msg.timestamp ? new Date(msg.timestamp).getTime() : Date.now(),
						};

						// 处理用户消息的特殊格式
						if (msg.role === 'user') {
							// 确保 content 是数组且有内容
							if (Array.isArray(msg.content) && msg.content.length > 0) {
								// 处理不同类型的内容
								const textContent = msg.content.find(item => item.type === 'text');
								const imageContent = msg.content.find(item => item.type === 'image');
								
								return {
									...baseMessage,
									content: textContent ? textContent.text : '',
									image: imageContent ? imageContent.url : undefined
								};
							}
							return {
								...baseMessage,
								content: '无法显示的消息'
							};
						} else {
							// AI 消息直接使用 content
							return {
								...baseMessage,
								content: msg.content,
								isPlaying: false // 添加语音播放状态
							};
						}
					});

					// 滚动到底部
					this.$nextTick(() => {
						this.scrollToBottom();
					});
				} else {
					throw new Error('获取消息失败');
				}
			} catch (error) {
				console.error('加载会话消息失败:', error);
				uni.showToast({
					title: '加载消息失败',
					icon: 'none'
				});
			} finally {
				uni.hideLoading();
			}
		},
		goToFuzzyKnowledge() {
			this.showSidebar = false;
			setTimeout(() => {
				uni.navigateTo({
					url: '/pages/fuzzy-knowledge/fuzzy-knowledge',
					fail: (err) => {
						console.error('导航失败：', err);
						uni.showToast({
							title: '页面跳转失败',
							icon: 'none'
						});
					}
				});
			}, 300);
		},
		goToDailyQuestion() {
			this.showSidebar = false;
			setTimeout(() => {
				uni.navigateTo({
					url: '/pages/daily-question/daily-question',
					fail: (err) => {
						console.error('导航失败：', err);
						uni.showToast({
							title: '页面跳转失败',
							icon: 'none'
						});
					}
				});
			}, 300);
		},
		// 播放试听
		playPreview() {
			if (!this.tempVoiceFile) return;
			
			if (this.isPreviewPlaying) {
				// 如果正在播放，则停止
				audioManager.stop();
				this.isPreviewPlaying = false;
				return;
			}
			
			// 播放录音
			audioManager.src = this.tempVoiceFile;
			audioManager.play();
			this.isPreviewPlaying = true;
			
			// 监听播放结束
			audioManager.onEnded(() => {
				this.isPreviewPlaying = false;
			});
			
			// 监听播放错误
			audioManager.onError((res) => {
				console.error('试听播放失败:', res);
				this.isPreviewPlaying = false;
				uni.showToast({
					title: '播放失败',
					icon: 'none'
				});
			});
		},
		
		// 确认提交录音
		async confirmVoiceSubmit() {
			if (!this.tempVoiceFile) return;
			
			try {
				// 停止可能的试听播放
				if (this.isPreviewPlaying) {
					audioManager.stop();
					this.isPreviewPlaying = false;
				}
				
				// 显示加载提示
				uni.showLoading({
					title: '发送中...',
					mask: true
				});
				
				// 添加用户语音消息到聊天记录
				const userMessage = {
					type: 'user',
					messageType: 'voice',
					content: this.tempVoiceFile,
					duration: Math.ceil((Date.now() - this._recordStartTime) / 1000), // 将毫秒转换为秒并向上取整
					time: Date.now()
				};
				
				this.chatMessages.push(userMessage);
				this.isAiTyping = true;
				
				// 直接发送语音文件到对话接口
				const response = await uni.uploadFile({
					url: 'http://10.65.1.110:8001/chat',
					filePath: this.tempVoiceFile,
					name: 'audio_file',
					formData: {
						user_id: '1',
						session_id: this.sessionId || ''
					},
					header: {
						'Accept': '*/*'
					}
				});
				
				if (response.statusCode === 200) {
					const result = JSON.parse(response.data);
					
					// 添加 AI 回复消息
					const aiMessage = {
						type: 'ai',
						content: result.response || result,
						followUpSuggestions: result.follow_up_suggestions || [],
						time: Date.now(),
						isPlaying: false
					};
					
					this.chatMessages.push(aiMessage);
					
					// 保存到本地存储
					uni.setStorageSync('chatHistory', this.chatMessages);
					
					// 滚动到底部
					this.$nextTick(() => {
						this.scrollToBottom();
					});
				} else {
					throw new Error('发送失败');
				}
				
			} catch (error) {
				console.error('语音对话失败:', error);
				uni.showToast({
					title: error.message || '发送失败',
					icon: 'none'
				});
			} finally {
				// 清理临时状态
				this.tempVoiceFile = null;
				this.isPreviewingVoice = false;
				this.showVoiceBtn = false;
				this.isAiTyping = false;
				uni.hideLoading();
			}
		},
		
		// 取消录音
		cancelVoiceSubmit() {
			// 停止可能的试听播放
			if (this.isPreviewPlaying) {
				audioManager.stop();
				this.isPreviewPlaying = false;
			}
			
			// 清理临时状态
			this.tempVoiceFile = null;
			this.isPreviewingVoice = false;
			this.showVoiceBtn = false;
		},
		async startNewChat(skipConfirm = false) {
			try {
				// 如果不是跳过确认，则显示确认弹窗
				if (!skipConfirm) {
					const res = await new Promise((resolve, reject) => {
						uni.showModal({
							title: '新对话',
							content: '是否开始新的对话？当前对话将会保存。',
							confirmText: '确定',
							cancelText: '取消',
							success: (result) => resolve(result),
							fail: (error) => reject(error)
						});
					});
					
					if (!res.confirm) return;
				}
				
				// 清空当前会话
				this.chatMessages = [];
				this.sessionId = null;  // 清空 session_id
				this.tempImage = '';
				
				try {
					// 调用后端API创建新会话
					const response = await uni.request({
						url: 'http://10.65.1.110:8001/chat',
						method: 'POST',
						data: {
							text: '你好',
							user_id: 1,
							session_id: ''  // 空session_id表示创建新会话
						}
					});
					
					if (response.statusCode === 200 && response.data.session_id) {
						// 保存新的session_id
						this.sessionId = response.data.session_id;
					}
				} catch (error) {
					console.error('创建新会话失败:', error);
					throw new Error('创建新会话失败');
				}
				
				// 显示 AI 欢迎消息
				this.chatMessages.push({
					type: 'ai',
					content: '你好，我是AI老师。',
					time: Date.now()
				});
				
				// 滚动到顶部
				this.$nextTick(() => {
					this.scrollTop = 0;
				});
				
			} catch (error) {
				console.error('开始新对话失败:', error);
				uni.showToast({
					title: '操作失败',
					icon: 'none'
				});
			}
		},
		async handleLogout() {
			try {
				const res = await new Promise((resolve, reject) => {
					uni.showModal({
						title: '退出登录',
						content: '确定要退出登录吗？',
						confirmText: '确定',
						cancelText: '取消',
						success: (result) => resolve(result),
						fail: (error) => reject(error)
					});
				});
				
				if (!res.confirm) return;
				
				// 清除用户信息
				uni.removeStorageSync('userInfo');
				// 清除每日一题缓存
				uni.removeStorageSync('dailyQuestion');
				uni.removeStorageSync('lastQuestionDate');
				
				// 清除会话信息
				this.chatMessages = [];
				this.sessionId = null;
				
				// 关闭侧边栏
				this.showSidebar = false;
				
				// 显示退出成功提示
				uni.showToast({
					title: '已退出登录',
					icon: 'success',
					duration: 1500
				});
				
				// 延迟跳转到登录页
				setTimeout(() => {
					uni.reLaunch({
						url: '/pages/login/login'
					});
				}, 1500);
				
			} catch (error) {
				console.error('退出登录失败:', error);
				uni.showToast({
					title: '操作失败',
					icon: 'none'
				});
			}
		}
	},
	onLoad(options) {
		// 获取状态栏高度
		this.getStatusBarHeight();
		
		// 初始化音频管理器
		this.audioManager = uni.createInnerAudioContext();
		
		// 如果有会话ID，设置到组件状态中
		if (options.sessionId) {
			console.log('Loading session:', options.sessionId); // 添加日志
			this.sessionId = options.sessionId;
			this.loadSessionMessages(options.sessionId);
		}
		
		// 初始化其他必要的监听器...

		// 只在支持录音的平台上初始化录音监听
		if (this.isRecordingSupported && recorderManager) {
			// 记录开始录音的时间
			recorderManager.onStart(() => {
				console.log('录音开始');
				this._recordStartTime = Date.now();
			});

			// 监听录音结束事件
			recorderManager.onStop(async (res) => {
				console.log('录音结束:', res);
				const duration = Date.now() - this._recordStartTime;
				console.log('录音时长:', duration, 'ms');
				
				if (res.tempFilePath) {
					try {
						const fileInfo = await uni.getFileInfo({
							filePath: res.tempFilePath
						});
						console.log('录音文件信息:', fileInfo);
						
						if (fileInfo.size < 1024) {
							uni.showToast({
								title: '录音无效，请重试',
								icon: 'none'
							});
							return;
						}
						
						// 保存临时文件并显示预览界面
						this.tempVoiceFile = res.tempFilePath;
						this.isPreviewingVoice = true;
						
					} catch (error) {
						console.error('获取录音文件信息失败:', error);
						uni.showToast({
							title: '录音失败，请重试',
							icon: 'none'
						});
					}
				} else {
					console.error('未获取到录音文件路径');
					uni.showToast({
						title: '录音失败',
						icon: 'none'
					});
				}
			});

			// 监听录音错误事件
			recorderManager.onError((res) => {
				console.error('录音错误:', res);
				this.isRecording = false;
				this.showVoiceBtn = false;
				uni.showToast({
					title: '录音失败: ' + (res.errMsg || '未知错误'),
					icon: 'none'
				});
			});

			// 监听录音开始事件
			recorderManager.onStart(() => {
				console.log('录音开始');
			});
		}

		// 添加新对话事件监听
		uni.$on('startNewChat', (skipConfirm = true) => {
			this.startNewChat(skipConfirm);
		});
	},
	onUnload() {
		// 移除新对话事件监听
		uni.$off('startNewChat');
	}
}
</script>

<style>
.container {
	display: flex;
	flex-direction: column;
	height: 100vh;
	background-color: #1c1c1e;
	position: relative;
	overflow: hidden; /* 防止整个容器滚动 */
}

.status-bar {
	width: 100%;
	background-color: #1c1c1e;
	position: fixed;
	top: 0;
	left: 0;
	z-index: 999;
}

.header {
	padding: 10px 16px;
	display: flex;
	justify-content: space-between;
	align-items: center;
	color: #ffffff;
	border-bottom: 1px solid #333;
	background-color: #1c1c1e;
	position: fixed;
	top: var(--status-bar-height);
	left: 0;
	right: 0;
	z-index: 998;
}

.left, .right {
	display: flex;
	align-items: center;
}

.center {
	font-size: 18px;
	font-weight: bold;
}

.icon {
	margin-left: 15px;
	font-size: 20px;
}

.chat-container {
	flex: 1;
	padding: 16px;
	padding-top: calc(var(--status-bar-height) + 56px); /* 状态栏高度 + header高度 */
	height: calc(100vh - var(--status-bar-height) - 180px);
	overflow-y: scroll;
	-webkit-overflow-scrolling: touch;
	position: relative;
	background-color: #1c1c1e;
	margin-bottom: calc(120px + env(safe-area-inset-bottom));
}

.chat-container::-webkit-scrollbar {
	width: 4px;
}

.chat-container::-webkit-scrollbar-thumb {
	background-color: rgba(255, 255, 255, 0.2);
	border-radius: 2px;
}

.message {
	display: flex;
	margin-bottom: 20px;
	max-width: 100%;
}

.avatar {
	width: 40px;
	height: 40px;
	border-radius: 50%;
	margin-right: 10px;
}

.message-content {
	background-color: #2c2c2e;
	padding: 12px;
	border-radius: 12px;
	max-width: 70%;
	color: #ffffff;
	word-break: break-all;
	display: flex;
	flex-direction: column;
}

.suggestions {
	margin-top: 20px;
}

.suggestion-title {
	color: #808080;
	font-size: 14px;
	margin-bottom: 10px;
}

.suggestion-item {
	background-color: rgba(0, 0, 0, 0.2);
	padding: 8px 12px;
	border-radius: 16px;
	margin-bottom: 8px;
	cursor: pointer;
	transition: background-color 0.2s;
}

.suggestion-item:active {
	background-color: rgba(0, 0, 0, 0.3);
}

.suggestion-text {
	color: #007AFF;
	font-size: 14px;
}

.fire-icon {
	margin-right: 8px;
}

.footer {
	padding: 10px 16px;
	background-color: #1c1c1e;
	position: fixed;
	bottom: 0;
	left: 0;
	right: 0;
	z-index: 997;
	border-top: 1px solid #333;
}

.tool-bar {
	display: flex;
	justify-content: space-around;
	margin-bottom: 10px;
}

.tool-item {
	display: flex;
	flex-direction: column;
	align-items: center;
	color: #808080;
	font-size: 12px;
}

.tool-icon {
	width: 24px;
	height: 24px;
	margin-bottom: 4px;
}

.input-area {
	display: flex;
	align-items: center;
	background-color: #2c2c2e;
	padding: 8px 12px;
	border-radius: 20px;
	margin-bottom: env(safe-area-inset-bottom);
}

.chat-input {
	flex: 1;
	background: none;
	border: none;
	color: #ffffff;
	margin: 0 10px;
	height: 36px;
}

.mic-icon, .plus-icon, .send-icon {
	font-size: 20px;
	padding: 0 8px;
	color: #808080;
}

.mask {
	position: fixed;
	top: 0;
	left: 0;
	right: 0;
	bottom: 0;
	background-color: rgba(0, 0, 0, 0.5);
	z-index: 998;
}

.sidebar {
	position: fixed;
	top: 0;
	left: -280px;
	width: 280px;
	height: 100%;
	background-color: #2c2c2e;
	z-index: 999;
	transition: transform 0.3s ease;
	padding: 20px 0;
}

.sidebar-show {
	transform: translateX(280px);
}

.sidebar-header {
	padding: 20px;
	border-bottom: 1px solid #3c3c3e;
	display: flex;
	align-items: center;
	margin-bottom: 20px;
}

.user-avatar {
	width: 50px;
	height: 50px;
	border-radius: 25px;
	margin-right: 15px;
}

.user-name {
	color: #ffffff;
	font-size: 18px;
}

.sidebar-content {
	padding: 0 20px;
}

.sidebar-item {
	display: flex;
	align-items: center;
	padding: 15px 0;
	color: #ffffff;
	border-bottom: 1px solid #3c3c3e;
	cursor: pointer; /* 添加鼠标指针样式 */
}

.sidebar-item:active {
	opacity: 0.7; /* 添加点击反馈 */
}

.sidebar-icon {
	margin-right: 15px;
	font-size: 20px;
}

.send-btn {
	font-size: 16px;
	color: #007AFF;
	padding: 0 8px;
}

/* 添加新的样式 */
.voice-input-area {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 8px 16px;
	width: 100%;
}

.voice-btn {
	flex: 1;
	background-color: #2c2c2e;
	color: #ffffff;
	padding: 12px;
	text-align: center;
	border-radius: 20px;
	margin-right: 10px;
}

.voice-btn.recording {
	background-color: #404040;
}

.cancel-voice {
	color: #007AFF;
	font-size: 16px;
	padding: 8px;
}

/* 添加新的样式 */
.user-message {
	flex-direction: row-reverse;
}

.user-message .message-content {
	background-color: #007AFF;
	margin-left: 0;
	margin-right: 10px;
}

.typing {
	opacity: 0.8;
}

/* 确保消息内容样式正确 */
.message-content {
	background-color: #2c2c2e;
	padding: 12px;
	border-radius: 12px;
	max-width: 70%;
	color: #ffffff;
	word-break: break-all;
}

/* 添加语音消息相关样式 */
.voice-message {
	min-width: 80px;
	cursor: pointer;
}

.voice-content {
	display: flex;
	align-items: center;
	gap: 8px;
}

.voice-icon {
	font-size: 20px;
}

.voice-duration {
	color: #808080;
	font-size: 14px;
}

.playing-indicator {
	color: #007AFF;
	animation: blink 1s infinite;
}

@keyframes blink {
	0% { opacity: 1; }
	50% { opacity: 0.5; }
	100% { opacity: 1; }
}

.preview-area {
	padding: 8px 16px;
	display: flex;
	align-items: center;
	background-color: #1c1c1e;
}

.preview-image {
	width: 60px;
	height: 60px;
	border-radius: 8px;
	margin-right: 10px;
}

.preview-close {
	position: absolute;
	top: -6px;
	right: -6px;
	background: rgba(0,0,0,0.6);
	border-radius: 50%;
	width: 20px;
	height: 20px;
	display: flex;
	align-items: center;
	justify-content: center;
	color: #fff;
}

.preview-wrapper {
	position: relative;
}

/* 添加消息图片样式 */
.message-image {
	max-width: 200px;
	width: 100%;
	border-radius: 8px;
	margin-bottom: 8px;
}

/* 调整消息内容样式以适应图片 */
.message-content {
	background-color: #2c2c2e;
	padding: 12px;
	border-radius: 12px;
	max-width: 70%;
	color: #ffffff;
	word-break: break-all;
	display: flex;
	flex-direction: column;
}

.user-message .message-content {
	background-color: #007AFF;
}

/* 添加 Markdown 相关样式 */
.message-content >>> .mp-html {
    color: #ffffff;
}

.message-content >>> pre {
    background-color: #1e1e1e;
    padding: 10px;
    border-radius: 4px;
    overflow-x: auto;
}

.message-content >>> code {
    font-family: monospace;
    background-color: rgba(0, 0, 0, 0.2);
    padding: 2px 4px;
    border-radius: 3px;
}

.message-content >>> math {
    display: block;
    overflow-x: auto;
    padding: 8px;
    background-color: rgba(0, 0, 0, 0.1);
    border-radius: 4px;
    margin: 4px 0;
}

/* AI 消息内容的样式调整 */
.ai-message .message-content {
    padding: 16px;
}

/* 代码块样式 */
.message-content >>> pre {
    background-color: #1e1e1e;
    padding: 10px;
    border-radius: 4px;
    overflow-x: auto;
    margin: 8px 0;
}

.message-content >>> code {
    font-family: monospace;
    background-color: rgba(0, 0, 0, 0.2);
    padding: 2px 4px;
    border-radius: 3px;
    color: #e6e6e6;
}

/* 数学公式样式 */
.message-content >>> .math {
    display: block;
    overflow-x: auto;
    padding: 8px;
    background-color: rgba(0, 0, 0, 0.1);
    border-radius: 4px;
    margin: 4px 0;
    font-family: monospace;
}

/* 列表样式 */
.message-content >>> ul,
.message-content >>> ol {
    padding-left: 20px;
    margin: 8px 0;
}

/* 引用样式 */
.message-content >>> blockquote {
    border-left: 4px solid #404040;
    margin: 8px 0;
    padding-left: 12px;
    color: #a0a0a0;
}

/* Markdown 内容样式 */
.markdown-content {
    color: #ffffff;
    line-height: 1.5;
}

/* 代码块样式 */
.markdown-content pre {
    background-color: #1e1e1e;
    padding: 10px;
    border-radius: 4px;
    overflow-x: auto;
    margin: 8px 0;
}

.markdown-content code {
    font-family: monospace;
    background-color: rgba(0, 0, 0, 0.2);
    padding: 2px 4px;
    border-radius: 3px;
    color: #e6e6e6;
}

/* 数学公式样式 */
.markdown-content .math {
    display: block;
    overflow-x: auto;
    padding: 8px;
    background-color: rgba(0, 0, 0, 0.1);
    border-radius: 4px;
    margin: 4px 0;
    font-family: monospace;
}

/* 列表样式 */
.markdown-content ul,
.markdown-content ol {
    padding-left: 20px;
    margin: 8px 0;
}

/* 引用样式 */
.markdown-content blockquote {
    border-left: 4px solid #404040;
    margin: 8px 0;
    padding-left: 12px;
    color: #a0a0a0;
}

/* AI 回复语音控制样式 */
.ai-response {
    display: flex;
    flex-direction: column;
    width: 100%;
}

.ai-voice-control {
    display: flex;
    align-items: center;
    margin-top: 8px;
    padding: 6px 12px;
    background-color: rgba(0, 0, 0, 0.2);
    border-radius: 16px;
    align-self: flex-start;
    cursor: pointer;
}

.ai-voice-control:active {
    opacity: 0.7;
}

.ai-voice-control .voice-icon {
    font-size: 18px;
    margin-right: 6px;
}

.ai-voice-control .voice-text {
    font-size: 14px;
    color: #ffffff;
}

/* 添加建议问题样式 */
.follow-up-suggestions {
    margin-top: 16px;
    width: 100%;
}

.suggestions-title {
    font-size: 14px;
    color: #808080;
    margin-bottom: 8px;
}

.suggestion-item {
    background-color: rgba(0, 0, 0, 0.2);
    padding: 8px;
    border-radius: 4px;
    color: #ffffff;
    display: flex;
    align-items: center;
    margin-bottom: 8px;
}

.suggestion-text {
    margin-left: 8px;
    font-size: 14px;
    color: #ffffff;
}

/* 适配 iPhone X 等带有底部安全区域的设备 */
@supports (padding-bottom: env(safe-area-inset-bottom)) {
    .footer {
        padding-bottom: calc(10px + env(safe-area-inset-bottom));
    }
}

/* 添加试听界面样式 */
.voice-preview {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    background-color: #2c2c2e;
    padding: 16px;
    border-top: 1px solid #3c3c3e;
    z-index: 999;
}

.preview-controls {
    display: flex;
    justify-content: space-around;
    align-items: center;
    padding: 10px 0;
}

.preview-btn, .submit-btn, .cancel-btn {
    padding: 8px 20px;
    border-radius: 20px;
    font-size: 14px;
    border: none;
}

.preview-btn {
    background-color: #2c2c2e;
    color: #007AFF;
    border: 1px solid #007AFF;
}

.preview-btn.playing {
    background-color: #007AFF;
    color: #ffffff;
}

.submit-btn {
    background-color: #007AFF;
    color: #ffffff;
}

.cancel-btn {
    background-color: #2c2c2e;
    color: #ff3b30;
    border: 1px solid #ff3b30;
}

/* 在 style 标签中添加 */
.katex-display {
    margin: 1em 0;
    overflow-x: auto;
    overflow-y: hidden;
}

.katex {
    font-size: 1.1em;
}

/* 行内公式样式 */
.katex-inline {
    display: inline-block;
    margin: 0 0.2em;
}

/* 块级公式样式 */
.katex-block {
    display: block;
    margin: 1em 0;
    text-align: center;
}

/* 处理公式过长的情况 */
.katex-display > .katex {
    display: inline-block;
    white-space: nowrap;
    max-width: 100%;
    overflow-x: auto;
    text-align: initial;
}

/* 数学公式背景 */
.math-block {
    background: rgba(0, 0, 0, 0.05);
    padding: 10px;
    border-radius: 4px;
    margin: 10px 0;
    overflow-x: auto;
}
</style>
