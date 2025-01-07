<template>
	<view class="container">
		<!-- 题目卡片 -->
		<view class="question-card">
			<view class="card-header">
				<text class="title">每日一题</text>
				<text class="date">{{ formatDate() }}</text>
			</view>
			<view class="knowledge-points">
				<text class="tag" v-for="(point, index) in knowledgePoints" :key="index">
					{{ point }}
				</text>
			</view>
			<view class="question-content">
				<text>{{ question }}</text>
			</view>
		</view>
		
		<!-- 答题区域 -->
		<view class="answer-area">
			<view class="upload-box" @tap="chooseImage" v-if="!answerImage">
				<text class="upload-icon">📷</text>
				<text class="upload-text">点击上传答题图片</text>
			</view>
			<view class="preview-box" v-else>
				<image 
					:src="answerImage" 
					mode="aspectFit" 
					class="preview-image"
					@tap="previewImage"
				/>
				<text class="delete-btn" @tap.stop="deleteImage">×</text>
			</view>
		</view>
		
		<!-- 添加解析和答案区域 -->
		<view class="solution-area" v-if="showSolution">
			<view class="solution-card">
				<view class="solution-header">
					<text class="solution-title">解析</text>
				</view>
				<view class="solution-content">
					<text>{{ analysis }}</text>
				</view>
			</view>
			
			<view class="solution-card">
				<view class="solution-header">
					<text class="solution-title">答案</text>
				</view>
				<view class="solution-content">
					<text>{{ answer }}</text>
				</view>
			</view>
		</view>
		
		<!-- 提交按钮 -->
		<button 
			v-if="!showSolution"
			class="submit-btn" 
			:disabled="!answerImage" 
			:class="{ 'disabled': !answerImage }"
			@tap="submitAnswer"
		>
			提交答案
		</button>
	</view>
</template>

<script>
export default {
	data() {
		return {
			question: '',
			knowledgePoints: ['一元一次方程式', '勾股定理'],
			answerImage: '',
			analysis: '',
			answer: '',
			followUpSuggestions: [],
			showSolution: false,
		}
	},
	methods: {
		formatDate() {
			const date = new Date();
			return `${date.getFullYear()}.${String(date.getMonth() + 1).padStart(2, '0')}.${String(date.getDate()).padStart(2, '0')}`;
		},
		
		// 检查是否需要更新题目
		needUpdateQuestion() {
			const lastQuestionDate = uni.getStorageSync('lastQuestionDate');
			const currentDate = this.formatDate();
			return lastQuestionDate !== currentDate;
		},
		
		// 保存题目到本地存储
		saveQuestionToStorage(questionData) {
			uni.setStorageSync('dailyQuestion', questionData);
			uni.setStorageSync('lastQuestionDate', this.formatDate());
		},
		
		// 从本地存储加载题目
		loadQuestionFromStorage() {
			const questionData = uni.getStorageSync('dailyQuestion');
			if (questionData) {
				const { question, analysis, answer } = questionData;
				this.question = question;
				this.analysis = analysis;
				this.answer = answer;
			}
		},
		
		async loadQuestion() {
			// 检查是否需要更新题目
			if (!this.needUpdateQuestion()) {
				this.loadQuestionFromStorage();
				return;
			}
			
			try {
				uni.showLoading({
					title: '加载中...',
					mask: true
				});
				
				const response = await uni.request({
					url: 'http://10.65.1.110:8001/generate_by_knowledge',
					method: 'POST',
					data: {
						knowledge_points: this.knowledgePoints
					}
				});
				
				if (response.statusCode === 200 && response.data) {
					const { question, analysis, answer } = response.data;
					
					// 处理数据
					const questionData = {
						question: question.replace(/[\[\]]/g, ''),
						analysis: analysis.replace(/[\[\]]/g, ''),
						answer: answer.replace(/[\[\]]/g, '')
					};
					
					// 更新状态
					this.question = questionData.question;
					this.analysis = questionData.analysis;
					this.answer = questionData.answer;
					
					// 保存到本地存储
					this.saveQuestionToStorage(questionData);
					
				} else {
					throw new Error('获取题目失败');
				}
			} catch (error) {
				console.error('加载题目失败:', error);
				uni.showToast({
					title: '加载题目失败',
					icon: 'none'
				});
			} finally {
				uni.hideLoading();
			}
		},
		
		chooseImage() {
			uni.chooseImage({
				count: 1,
				sizeType: ['compressed'],
				sourceType: ['camera', 'album'],
				success: (res) => {
					this.answerImage = res.tempFilePaths[0];
				},
				fail: (err) => {
					console.error('选择图片失败:', err);
					uni.showToast({
						title: '选择图片失败',
						icon: 'none'
					});
				}
			});
		},
		
		deleteImage() {
			this.answerImage = '';
		},
		
		previewImage() {
			if (this.answerImage) {
				uni.previewImage({
					urls: [this.answerImage],
					current: this.answerImage
				});
			}
		},
		
		async submitAnswer() {
			if (!this.answerImage) return;
			
			try {
				uni.showLoading({
					title: '提交中...',
					mask: true
				});
				
				// 上传图片后显示解析和答案
				this.showSolution = true;
				
				uni.showToast({
					title: '提交成功',
					icon: 'success'
				});
				
				// 滚动到解析区域
				this.$nextTick(() => {
					uni.pageScrollTo({
						selector: '.solution-area',
						duration: 300
					});
				});
				
			} catch (error) {
				console.error('提交答案失败:', error);
				uni.showToast({
					title: '提交失败',
					icon: 'none'
				});
			} finally {
				uni.hideLoading();
			}
		},
		
		// 添加跟进问题的处理方法
		askFollowUp(question) {
			uni.navigateTo({
				url: '/pages/index/index',
				success: () => {
					// 发送问题到聊天页面
					uni.$emit('askQuestion', question.replace(/[<>]/g, ''));
				}
			});
		}
	},
	onLoad() {
		this.loadQuestion();
	}
}
</script>

<style>
.container {
	padding: 20px;
	background-color: #1c1c1e;
	min-height: 100vh;
}

.question-card {
	background-color: #2c2c2e;
	border-radius: 12px;
	padding: 20px;
	margin-bottom: 20px;
}

.card-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-bottom: 16px;
}

.title {
	font-size: 20px;
	font-weight: bold;
	color: #ffffff;
}

.date {
	color: #808080;
	font-size: 14px;
}

.knowledge-points {
	display: flex;
	flex-wrap: wrap;
	gap: 8px;
	margin-bottom: 16px;
}

.tag {
	background-color: rgba(0, 122, 255, 0.1);
	color: #007AFF;
	padding: 4px 12px;
	border-radius: 16px;
	font-size: 12px;
}

.question-content {
	color: #ffffff;
	font-size: 16px;
	line-height: 1.6;
}

.answer-area {
	margin-bottom: 20px;
}

.upload-box {
	background-color: #2c2c2e;
	border-radius: 12px;
	height: 200px;
	display: flex;
	flex-direction: column;
	justify-content: center;
	align-items: center;
	border: 2px dashed #3c3c3e;
}

.upload-icon {
	font-size: 40px;
	margin-bottom: 10px;
}

.upload-text {
	color: #808080;
	font-size: 14px;
}

.preview-box {
	position: relative;
	width: 100%;
	height: 200px;
	border-radius: 12px;
	overflow: hidden;
}

.preview-image {
	width: 100%;
	height: 100%;
	object-fit: contain;
}

.delete-btn {
	position: absolute;
	top: 10px;
	right: 10px;
	width: 24px;
	height: 24px;
	background-color: rgba(0, 0, 0, 0.6);
	color: #ffffff;
	border-radius: 12px;
	display: flex;
	justify-content: center;
	align-items: center;
	font-size: 16px;
}

.submit-btn {
	background-color: #007AFF;
	color: #ffffff;
	border-radius: 12px;
	padding: 12px;
	font-size: 16px;
	width: 100%;
	border: none;
}

.submit-btn.disabled {
	background-color: #3c3c3e;
	color: #808080;
}

.submit-btn:active {
	opacity: 0.8;
}

/* 添加解析和答案区域的样式 */
.solution-area {
	margin-top: 30px;
}

.solution-card {
	background-color: #2c2c2e;
	border-radius: 12px;
	padding: 20px;
	margin-bottom: 20px;
}

.solution-header {
	margin-bottom: 16px;
}

.solution-title {
	font-size: 18px;
	font-weight: bold;
	color: #007AFF;
}

.solution-content {
	color: #ffffff;
	font-size: 16px;
	line-height: 1.6;
	white-space: pre-line; /* 保留换行符 */
}
</style> 