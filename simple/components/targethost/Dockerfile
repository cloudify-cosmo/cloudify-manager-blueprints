FROM phusion/baseimage

RUN apt-get update && \
    apt-get install -y sudo curl wget python
RUN rm -f /etc/service/sshd/down
RUN /etc/my_init.d/00_regen_ssh_host_keys.sh

CMD ["/sbin/my_init", "--enable-insecure-key"]